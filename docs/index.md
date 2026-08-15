---
title: Contributor tooling
type: explanation
summary: "How the tooling in this repository is organised and where each kind of work belongs."
audience: contributor
status: current
verified: 2026-08-15
---

# Contributor tooling

This directory documents the tooling used to build Shesh. None of it is
installed on a user's machine, which is why it lives here next to the tools
rather than in the product documentation.

If you are running Shesh rather than working on it, you want
[shesh-docs](https://github.com/gaganjainse/shesh-docs) instead.

## Product and tooling are separate

Development tooling and shipped code were once in the same repository. That
caused two concrete problems: contributors applied contributor-only procedures
to product code, and automated agents cloned the entire fleet for work that
touched a single component.

| Repository | Contains | Ships to users |
|---|---|---|
| `shesh-ecosystem` | Component manifest, channel lockfiles, resolution and licence gates | Yes |
| `shesh-workspace` | Session tooling, parallel-agent orchestration, credential helpers, evaluation scripts | No |
| `shesh-docs` | Operator and architecture documentation | Published, not installed |
| `shesh-docs-archive` | Superseded records | No |

Component repositories contain their own code, tests, and README, and nothing
else.

## Where work belongs

**Changing a capability.** Work in that component's repository and run its own
test suite. If the change alters the component's version or declared
capabilities, update the manifest in `shesh-ecosystem` as a separate change.

**Changing how components combine.** Work in `shesh-ecosystem`: the manifest,
the resolver, the licence gate, and the integration tests.

**Changing the contributor tooling.** Work here. This tooling is not gated by
the product's release channels, because it never reaches a user.

**Changing documentation.** Operator and architecture material goes in
`shesh-docs`. Component build instructions stay in that component's README.

Do not mix these in one change. Work spanning repositories should be a sequence
of changes with a stated order.

## Contents

### Working sessions

Long work spans sessions, and context is lost between them. These make handover
explicit rather than relying on memory.

- [Session protocol](session-protocol.md) — opening and closing a session.
- [Session guard](session-guard.md) — detecting a degraded session.
- [Session handoff](https://github.com/gaganjainse/shesh-docs/blob/main/src/session-handoff.md) — the state carried forward.
- [Next-session prompt](https://github.com/gaganjainse/shesh-docs/blob/main/src/next-session-prompt.md) — generated starting context.

### Credentials

Never commit a credential, and never paste one into an agent conversation. A
credential that has been exposed is revoked, not reused.

- [Credential handling](credential-handling.md) — encrypted storage of tokens.
- [GitHub authentication](github-authentication.md) — how tools resolve
  credentials at call time.

### Parallel agents

- [Running agents in parallel](parallel-agents.md) — coordination and locking.
- [Agent prompts](https://github.com/gaganjainse/shesh-docs/blob/main/src/agent-prompts.md) — the prompts used to brief workers.
- [Set up a worker](set-up-a-worker.md) — prepare a minimal workspace.
- [Clone efficiency](clone-efficiency.md) — fetch only what a task needs.
- [Low-bandwidth mode](low-bandwidth-mode.md) — working with limited connectivity.

The failure mode that motivated the locking mechanisms is recorded in the
[2026-08-11 collision post-mortem](https://github.com/gaganjainse/shesh-docs-archive/blob/main/src/incident-2026-08-11-swarm-collision.md).

### Model quality

The installed system must produce acceptable results from a small local model on
constrained hardware. Quality therefore cannot be assumed from the model; it has
to come from bounded prompts, validated output, and gates that check results.

- [Model-agnostic quality](model-agnostic-quality.md) — the strategy.
- [LLM adapter](llm-adapter.md) — the five-layer output guard.
- [Model router](model-router.md) — capability-based provider selection.
- [Evaluation harness](evaluation-harness.md) — scoring changes before promotion.

### Other

- [Documentation pipeline](documentation-pipeline.md) — how the book is built and
  validated.
- [Reusable infrastructure](reusable-infrastructure.md) — upstream tracking and
  adaptation tooling.
- [Desktop build prompts](https://github.com/gaganjainse/shesh-docs/blob/main/src/desktop-build-prompts.md) — phase-by-phase build notes.
- [Portfolio site](portfolio-site.md) — the personal site and its automation.

## Related

- [Architecture decision records](https://github.com/gaganjainse/shesh-docs/blob/main/src/governance/adr/index.md)
  — record a load-bearing decision before implementing it.
- [Documentation policy](https://github.com/gaganjainse/shesh-docs/blob/main/src/governance/documentation-policy.md)
  — the rules a documentation change must satisfy.
