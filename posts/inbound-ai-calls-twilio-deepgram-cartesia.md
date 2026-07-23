# Building an Inbound AI Call Line with Twilio, Deepgram, and Cartesia

*A caller dials your business number. An AI answers, understands, routes, takes action in your CRM, and hands off to a human exactly when it should. Here's the architecture, end to end.*

---

Voice is the last unautomated front door of most businesses. Web forms feed your CRM, email gets filtered and routed — but the phone still rings until a human picks up, and every missed call is a missed lead or an unhappy customer.

For **Helix**, the CRM/customer-data platform I'm building, I wanted the phone to be a first-class, automated channel: an AI receptionist that answers instantly, figures out who's calling and why, does real work (opens tickets, qualifies leads, books follow-ups), and escalates to humans with full context. This post walks through the stack that makes it work — **Twilio for telephony, Deepgram for speech-to-text, Cartesia for text-to-speech** — and the engineering decisions that matter more than the vendor list.

## The pipeline at a glance

```
Caller
  │  (PSTN)
  ▼
Twilio  ──── media stream (WebSocket, 8kHz μ-law audio) ────►  Voice service
                                                                 │
                              ┌──────────────────────────────────┤
                              ▼                                  ▼
                    Deepgram (streaming STT)              Flow engine (the "brain")
                    partial + final transcripts           intent routing, CRM actions,
                              │                           human-approval gates
                              └────────────► LLM turn ◄──────────┘
                                                │
                                                ▼
                                     Cartesia (streaming TTS)
                                                │
Twilio ◄──── synthesized audio frames ──────────┘
  │
  ▼
Caller hears the reply  (target: under ~1 second after they stop talking)
```

Three specialized vendors, one WebSocket each, and your own service in the middle. The vendors are swappable; the middle is where the product lives.

## Step 1: Twilio — get the audio as a stream, not a recording

Point your Twilio number's webhook at your service. Instead of the classic "record a voicemail" pattern, respond with TwiML that opens a **bidirectional media stream**:

```xml
<Response>
  <Connect>
    <Stream url="wss://voice.yourdomain.com/twilio/media" />
  </Connect>
</Response>
```

From that moment, Twilio sends you the caller's audio as base64 μ-law frames over a WebSocket, and plays back any audio you send on the same socket. This is the decision that makes everything else possible: **you're now in a real-time conversation loop, not a request/response IVR.** Keep the call SID — it's your correlation key for everything downstream.

## Step 2: Deepgram — words while they're still being spoken

Forward the audio frames straight into Deepgram's streaming API. Two features matter enormously:

- **Interim results.** You receive partial transcripts while the caller is mid-sentence. You can't act on them yet, but they let you *prepare* — warm the next model call, prefetch the CRM record for a spoken email address.
- **Endpointing.** Deepgram tells you when the speaker has finished a thought (`speech_final`). That signal — not a fixed silence timer — is when your agent should start thinking. Get this wrong and your AI either interrupts callers or leaves awkward three-second gaps. Tune the endpointing window (~300ms works for us) before you tune anything else.

## Step 3: The brain — a flow graph, not one giant prompt

Here's where most tutorials stop ("...then send the transcript to an LLM") and where real systems begin. A production call can't run on vibes; it runs on a **flow definition** — a graph our engine executes per call:

```
[trigger: inbound_call]
        │
        ▼
[intent_router]  "Why are you calling?"
   ├─ existing_customer/support ──► [agent: triage] ──► [action: open_ticket] ──► [human_task: support queue w/ SLA]
   ├─ new_prospect ──────────────► [agent: qualify] ──► [action: create_lead] ──► [enroll_journey: sales follow-up]
   └─ anything_else ─────────────► [human_checkpoint: warm transfer]
```

The LLM does what it's uniquely good for — understanding messy human speech and choosing among *declared* outcomes — while the graph guarantees what the business needs guaranteed:

- **Every agent node must declare its possible outcomes, and `escalate_human` is mandatory.** The AI always has a structured way to give up. Schema validation rejects any flow where it doesn't.
- **Consequential actions pass a gate.** Anything irreversible or money-touching (issuing a refund, sending a contract) runs through a human-approval checkpoint. The call doesn't stall — the AI tells the caller "you'll get a confirmation shortly," the flow *pauses*, and a human approves or denies from a queue. On approval, the flow resumes exactly where it paused.
- **Everything is ledgered.** Every node execution — transcript in, decision out, cost, latency — lands in an audit ledger. When a customer says "your AI told me X," you can replay the call decision by decision.

The unglamorous part that took real engineering: **call completion resumes the flow.** When Twilio reports the call ended, a webhook advances the paused flow instance — so post-call work (logging the outcome, scheduling the follow-up, emailing the transcript) runs automatically, and busy/no-answer/failed calls each take their own explicit path instead of leaving zombie state.

## Step 4: Cartesia — a voice fast enough to feel human

Text-to-speech quality is judged in your first second, not your best sentence. Cartesia's streaming synthesis returns first audio in tens of milliseconds, which enables the trick that makes the whole thing feel alive: **stream the LLM's reply into TTS sentence-by-sentence as it's generated.** The caller hears the beginning of the answer while the rest is still being written. Total silence between caller and reply stays around a second — inside the rhythm of human conversation.

Convert Cartesia's output to 8kHz μ-law, chunk it into frames, and write it back down the Twilio socket. One more essential detail: **barge-in.** If Deepgram detects the caller speaking while your audio is playing, stop sending frames immediately and clear Twilio's buffer. An AI that talks over people gets hung up on.

## The latency budget

Everything above is in service of one number — the pause after the caller stops talking:

| Stage | Budget |
|---|---|
| Endpoint detection | ~300 ms |
| LLM first token (fast model for routing turns) | ~350 ms |
| TTS first audio | ~100 ms |
| Network + framing | ~150 ms |
| **Caller-perceived pause** | **~0.9 s** |

Two practical notes. Use a *fast* model for conversational turns and save your deepest model for the analysis steps that happen off the critical path. And measure the pause from the caller's side (call yourself and record it) — server-side numbers always flatter you.

## What I'd tell you to build first

1. **The echo skeleton** — Twilio stream in, same audio out. Proves your socket plumbing.
2. **The transcript loop** — Deepgram in the middle, print live transcripts. Tune endpointing here.
3. **A two-node flow** — intent router with `support`/`sales`/`escalate_human`, canned replies through Cartesia. This is already a useful receptionist.
4. **Real actions behind gates** — CRM writes, tickets with SLAs, human approval for anything consequential. This is where a demo becomes a system you can trust with customers.
5. **The failure matrix** — busy, no-answer, mid-call hangup, vendor timeout. Each gets an explicit, tested path. Voice reliability is entirely about the unhappy paths.

The vendors will keep leapfrogging each other on quality and price — architecture outlives them. Put a real flow engine with declared outcomes, approval gates, and an audit ledger in the middle, and the phone stops being your least automated channel and becomes your most accountable one.

---

*Part of a series on building Helix at MarketingOrchestration.io: [orchestrating a fleet of AI coding agents](orchestrating-a-fleet-of-ai-coding-agents.md) · [the 5-gate pipeline that keeps AI hallucinations out of production](minimizing-ai-hallucinations-5-gate-pipeline.md).*
