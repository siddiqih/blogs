# Orchestrating a Fleet of AI Coding Agents with GitHub as the Control Plane

*How I run six autonomous AI engineers around the clock — with heartbeats, task queues, and kill switches built entirely out of a Git repository.*

---

Most people use AI coding assistants one conversation at a time: ask a question, get some code, paste it in. I wanted something different. I'm building **Helix**, a multi-tenant CRM and customer-data platform, and the backlog was far bigger than one person — or one AI chat window — could handle.

So I built a fleet: **six AI coding agents ("nodes") running on separate machines, working the backlog 24/7**, coordinated by one lead agent and supervised by me. In its busiest sprint, the fleet and its lead shipped a full visual flow-builder canvas — six coordinated pull requests, all reviewed, tested, and merged to production — in under 24 hours.

The most surprising design decision: **the entire orchestration layer is just GitHub.** No Kubernetes, no message broker, no custom control server. Issues, branches, labels, and JSON files in a repo. Here's how it works, and why that constraint turned out to be a feature.

## Why GitHub as the control plane?

When you coordinate autonomous agents, you need four things:

1. **A task queue** — what should each agent work on next?
2. **Health monitoring** — is each agent alive, and what is it doing?
3. **A kill switch** — how do you stop everything *right now*?
4. **An audit trail** — who did what, when, and why?

Every one of those is something GitHub already does, if you squint:

- The task queue is **issues with labels**. A task is an issue labeled `node-task` with a role label (`role:backend-swe`, `role:frontend-swe`, `role:qa-engineer`…) and a priority. Assignment is a comment on a control issue. Retries are a label (`node-retry:1`). Escalation to a human is a label (`needs-human`).
- Health monitoring is **heartbeat files on a dedicated branch**. Every node commits a small JSON file to a `node-status` branch every few minutes:

```json
{
  "node_id": "node3",
  "status": "idle",
  "timestamp": "2026-07-23T16:02:12Z",
  "task": null,
  "agent_runner_version": "f230c4a0b5"
}
```

  Checking fleet health is one command: `git show origin/node-status:heartbeats/node3.json`. No dashboards to host, no metrics stack — and the *history* of every heartbeat is preserved for free, because it's Git.

- The kill switch is **a label on a pinned issue**. Each repo has a "Node Control Center" issue; adding the `nodes-paused` label halts the entire fleet. Any maintainer can do it from a phone.
- The audit trail is the one you already have: **commits, pull requests, and reviews**. Nothing an agent does is invisible, because the only way an agent can affect anything is through Git.

That last point is the real insight. Message brokers and custom control planes create *side channels* — ways for agents to act that don't leave a reviewable trace. When Git is the only interface, **every action an agent takes is inherently versioned, attributable, and reversible.**

## The cast: nodes, a lead, and a human

The fleet has three tiers, and the separation of powers matters more than the automation.

**The nodes (node1–node5 + core)** are the workhorses. Each runs a daemon that wakes on a schedule, reads its assignment from the control issue, pulls the latest main, does the work — Django models, React pages, tests — and opens a pull request. Nodes have role definitions (backend engineer, frontend engineer, QA engineer, reviewer) that scope what they're allowed to touch. A node's version field in its heartbeat tells me exactly which commit of the runner it's on, so a stale node is visible within minutes.

**The lead agent** (my day-to-day collaborator) does what a tech lead does: breaks epics into node-sized issues with pinned interface contracts, reviews every node PR against acceptance criteria, *fixes* problems directly rather than bouncing work back, and drives each PR through the release gates. One rule I enforce: **shared contracts flow one way.** When six agents build parts of one feature, the lead publishes the TypeScript interfaces first; fleet PRs import them and are forbidden from altering them. That single rule eliminated almost every integration conflict.

**The human (me)** sets priorities, makes architectural calls, and holds the approvals that never get delegated: production credentials, anything that spends money, and the final review gate. The system is designed so I can steer it from a phone — which is not a gimmick, it's the requirement. Fleet check-ins happen hourly whether I'm at a desk or not.

## What a task's life looks like

1. I write one line: *"Build the per-node autonomy stats endpoint."*
2. The lead expands it into an issue: acceptance criteria, the exact API contract, the files in play, the test expectations — and assigns it via the control issue.
3. A node picks it up on its next wake, builds it on a feature branch, opens a PR.
4. Continuous integration runs the full test suite. If it fails, the *lead* diagnoses and pushes fixes to the node's branch — the node's job is throughput, the lead's job is integrity.
5. The PR walks through a five-gate review pipeline (that pipeline is its own story — see my post on minimizing AI hallucinations) and merges.
6. Every node's next heartbeat reports the new main-branch version, confirming the whole fleet self-updated.

The economics are what you'd hope: nodes handle the parallelizable 70% — CRUD endpoints, UI panes, test suites — while the lead concentrates on the 30% where mistakes compound: money-handling code paths, migration safety, cross-cutting contracts.

## What went wrong (and what it taught me)

An honest orchestration story includes the failures:

- **Runaway side effects.** Early on, the heartbeat commits themselves triggered 62,000 preview builds in our hosting pipeline, starving production deploys. Lesson: the control plane's own traffic needs the same scrutiny as application traffic. We scoped build triggers to real code paths and the queue vanished.
- **Silent capability gaps.** A node "completed" a task that quietly did nothing because a background task module was never imported by the worker process. The heartbeats were green; the feature was dead. Lesson: green health checks tell you the agent is alive, not that the work is real — which is exactly why the review pipeline demands *evidence*, not status.
- **Duplicate work.** Two different queue entries described the same feature written two ways; a node rebuilt something that had shipped weeks earlier. Lesson: the lead now reconciles the queue against the codebase before dispatching, not after.

## Why this matters beyond my project

The pattern generalizes to any team experimenting with autonomous AI development:

- **Use infrastructure you already trust.** Your VCS is a distributed, authenticated, audit-logged database with a permission model your whole team understands. Start there before you build a bespoke agent platform.
- **Make the only interface a reviewable one.** Agents that can only act through pull requests can never act invisibly.
- **Separate throughput from integrity.** Many cheap agents generating work, one strong agent verifying it, one human owning judgment. Each tier checks the one below.
- **Design for the pocket.** If you can't pause the fleet, read its health, and approve its output from a phone, you don't control it — you cohabit with it.

Six agents, one repository, zero custom infrastructure. The future of software teams might look less like more headcount, and more like better orchestration.

---

*I'm building Helix at MarketingOrchestration.io. The companion posts cover the [five-gate pipeline that keeps AI hallucinations out of production](minimizing-ai-hallucinations-5-gate-pipeline.md) and [the AI phone line we built with Twilio, Deepgram, and Cartesia](inbound-ai-calls-twilio-deepgram-cartesia.md).*
