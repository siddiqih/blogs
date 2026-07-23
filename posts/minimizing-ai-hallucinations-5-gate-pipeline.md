# Minimizing AI Hallucinations in Production Code: the 5-Gate Pipeline

*AI agents write most of my platform's code. Here's the Git-native review pipeline that catches their confident mistakes before customers ever see them.*

---

Ask anyone who has used AI to write serious software and they'll tell you the same uncomfortable truth: **the failure mode isn't bad code — it's confident code.** An AI agent will tell you the feature works, describe the tests it "ran," and summarize a job well done. Sometimes all of that is true. Sometimes none of it is. The summary reads identically either way.

That's what "hallucination" means in a software context. Not a chatbot inventing a fake citation — an agent *believing its own work is finished when it isn't*.

I run a fleet of AI coding agents building **Helix**, a CRM/customer-data platform (see my post on [orchestrating the fleet](orchestrating-a-fleet-of-ai-coding-agents.md)). Early on I accepted a premise that changed the whole design: **you cannot prompt hallucination away — you have to build a system where hallucinations can't reach production.** My answer is a five-gate pipeline, implemented entirely with Git branch protection and CI, that every single pull request must survive. No exceptions, including for me.

## The core principle: evidence, not assertion

One sentence governs the whole pipeline:

> **"Code merged" is never "done." An item is done only when every claim about it is backed by evidence — a test run, a log entry, a screenshot, or an API response — attached to the pull request.**

An AI saying "the tests pass" is an assertion. A CI job that ran the tests and posted the green check is evidence. The pipeline's job is to convert every assertion into evidence or block the merge. Each gate exists because assertions and reality can diverge in a different way.

## The five gates

**Gate 1 — Continuous integration (machines check the basics).**
Every PR triggers unit tests, type checking, linting, and secret scanning. This is table stakes, but note what it does to hallucinations: an agent *cannot* claim the build passes — the build passes or the PR is red. About a third of all hallucinated "done" claims die right here, cheaply, in ten minutes.

**Gate 2 — L1 technical review (an AI checks the AI).**
A dedicated reviewer agent — a different agent from the author, with a different role prompt — reads the diff against the task's written acceptance criteria: logic errors, missed edge cases, security issues, tests that assert nothing. Using an AI to review an AI sounds circular, but it works for the same reason human peer review works: **the author's blind spots and the reviewer's blind spots are rarely the same.** The reviewer never has the author's motivated reasoning about its own work.

**Gate 3 — L2 architectural review (a human checks the design).**
A human maintainer reviews what machines are worst at judging: does this belong in the architecture? Does it create a coupling we'll regret? Should this exist at all? Note the ordering — the human reviews *after* the machines have burned down the mechanical errors, so human attention goes where human judgment is actually needed.

**Gate 4 — Full regression suite (the whole system, not just the diff).**
The entire test suite — every module, ~everything the platform does — runs against the PR with a hard coverage floor. This gate exists because the most dangerous AI mistakes aren't in the code the agent wrote; they're in the code it *broke three files away*. A diff-scoped review can't see that. A thousand tests can.

**Gate 5 — QA sign-off with published evidence.**
Last, a sign-off comment must be posted on the PR before a verification job will go green. The comment isn't a rubber stamp — it's a structured evidence dossier: which tests cover which acceptance criterion, what the failure-path behavior is, what was deliberately deferred. The gate is enforced by branch protection: no evidence comment, no merge. It's the pipeline's way of forcing someone — human or agent — to *write down the proof* while it's fresh, where auditors (or future debuggers) can find it.

## Does it actually catch anything?

In one 24-hour sprint, this pipeline caught three real bugs in AI-authored code that had sailed through the authoring agent's own testing — each one a textbook hallucination:

1. **A fail-open safety guard.** A guard was supposed to *block* AI autonomy around money-touching actions when classification failed. The submitted code caught all exceptions and returned "not money-class" — meaning any internal error would silently *widen* AI autonomy over spending. The author's summary said the guard was implemented. It was — backwards. Review at Gate 2/3 caught it; the fix inverted it to fail-closed with tests proving both failure paths.

2. **A rounding assumption.** A statistics endpoint expected `round(98.5)` to be `99`. Python uses banker's rounding; it's `98`. The agent's hand-written test encoded its own wrong belief — the full-suite gate surfaced the contradiction.

3. **A guardrail keyed on a value that was always null.** A rate-limiting cooldown was keyed on a profile ID that, in the code path being shipped, was never populated — so the cooldown could never engage. Everything compiled; every local test passed; the feature was a no-op. Only review against the *written acceptance criteria* ("cooldown must dedupe repeat firings per profile") exposed it.

None of these were exotic. All of them were the kind of thing a confident summary glosses over. That's the point.

## Why Git-native matters

The pipeline needs no custom infrastructure — it's branch protection rules, CI workflows, labels, and PR comments. That has three consequences I now consider non-negotiable:

- **It cannot be bypassed by an agent**, because the enforcement lives in the platform, not in the agent's instructions. A prompt can be ignored; a required status check cannot.
- **The evidence is permanent and public** (to the team). Every sign-off dossier lives on its PR forever. When something breaks in production, the first question — *what did we actually verify?* — has a written answer.
- **It's adoptable in an afternoon.** Any team on GitHub/GitLab can implement gates 1, 4, and 5 today with protection rules; gates 2 and 3 are a reviewer agent and a human rota.

## The deeper lesson

We spend a lot of energy trying to make AI models hallucinate less. That work matters, but for software teams it's the wrong end of the problem. Aviation didn't get safe by producing pilots who never err; it got safe with checklists, cross-checks, and instruments that don't take the pilot's word for anything.

Treat AI coding agents the same way. Let them be fast and fallible — and build the system that demands evidence at every door. My fleet merges AI-written code to a production system many times a day, and I sleep fine. Not because the agents stopped hallucinating.

Because hallucinations stopped mattering.

---

*Part of a series on building Helix at MarketingOrchestration.io: [orchestrating a fleet of AI coding agents](orchestrating-a-fleet-of-ai-coding-agents.md) · [building an inbound AI call line](inbound-ai-calls-twilio-deepgram-cartesia.md).*
