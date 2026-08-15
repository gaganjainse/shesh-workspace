# FACTORY.md

The working agreement for every agent and every person who changes anything in
this fleet. One set of rules, applied identically whether the worker is Claude,
Codex, Cursor, Gemini, or a human at a terminal.

This is the **factory**: how work is done. The **product** is what the work
produces. The two are never mixed. See [§2](#2-product-and-factory).

---

## 1. Taking input

Before acting on a request, resolve it into a **work item**. An item has a goal,
a scope, and a definition of done. A request that cannot be resolved into one is
not ready to start.

### Classify the request

| Class | Signal | Response |
|---|---|---|
| **Well-formed** | Goal, scope, and success criteria are all clear | Start. State the plan first if non-trivial. |
| **Under-specified** | Goal clear, scope or criteria missing | Ask up to three specific questions. Do not guess. |
| **Ambiguous** | Two readings would produce different work | Ask. Never pick one silently. |
| **Out of scope** | Belongs to another repository or layer | Say where it belongs; do not do it here. |
| **Unsafe** | Needs a credential, deletes data, or is irreversible | Refuse until explicitly confirmed. |

### Ask well

Ask **once**, batched, with concrete options. Do not interrogate across several
turns.

```
The request could mean either:
  (a) rename the directory and update every reference, or
  (b) add an alias and leave the existing name in place.
(a) is a breaking change for anyone with a clone. Which?
```

Never ask a question the repository already answers. Read first.

### Restate before large work

For anything spanning more than about three files, restate the goal in one
sentence and list the files you intend to touch. Wait for agreement. This costs
a few seconds and prevents the class of error that takes an hour to unwind.

---

## 2. Product and factory

The distinction most easily lost between sessions.

| | Product | Factory |
|---|---|---|
| **Test** | Does a user install this? | Does this only help build? |
| **Repositories** | `shesh-core`, `shesh-memory`, `shesh-orchestrator`, `shesh-harness`, `shesh-phone`, `shesh-omniroute`, `shesh-skills`, `shesh-voice`, `shesh-desktop`, `SheshAOS` | `shesh-workspace` |
| **Composition** | `shesh-ecosystem` — manifest, lockfiles, gates | — |
| **Documentation** | `shesh-docs` | `shesh-workspace/docs` |
| **Channels** | `devel` → `canary` → `stable` | None |
| **Gate** | `make check` before promotion | Tests only |
| **Standard** | Production. No stubs. | Pragmatic. May be rough. |

**Never** move factory tooling into a product repository to satisfy an import.
**Never** apply release gates to factory scripts.

---

## 3. Giving output

### Structure

Lead with the outcome. Then evidence. Then what remains.

```
Fixed the socket path; A2A now connects.       ← outcome first
The f-string prefix was missing, so os.getuid()
never ran. 5 regression tests added.            ← evidence
Budget projection (BUG-3) is still open.        ← what remains
```

### Rules

- **State what you did, not what you intended.** "Added a test" only if it exists.
- **Never report a test as passing without running it.** Paste real output.
- **Report failures as prominently as successes.** A buried failure is a lie.
- **Quantify.** "562 tests" not "all tests". "3 of 50 findings remain" not "mostly done".
- **Name what you did not do**, and why.
- No emoji. No exclamation marks. No self-congratulation.
- Uncertainty is stated: "I did not verify X" is always better than implying you did.

### Length

Match the work. A one-line fix gets a one-line report. Do not pad, and do not
summarise a large change into something that hides its risk.

---

## 4. Writing documents

Governed by the [style guide](https://github.com/gaganjainse/shesh-docs/blob/main/STYLEGUIDE.md),
enforced by `tools/check_docs.py`.

| Rule | Detail |
|---|---|
| One Diátaxis type per page | Tutorial, how-to, reference, or explanation. Never mixed. |
| Voice | Second person, present tense, active. |
| Headings | Sentence case. No emoji, no numeric prefixes. |
| Prohibited | First person, self-assessment ("clean", "robust"), filler ("simply", "just"), quoted chat prompts. |
| Facts | No volatile counts. Generate the page or give the command. |
| Single source | One fact in one place. Link, never copy. |
| Front matter | `title`, `type`, `summary`, `audience`, `status`, `verified`. |

`verified` is set only when a person actually checked the claims against code.

---

## 5. Editing files

1. **Read the whole file** before changing any of it.
2. **Smallest change** that completes the item. Do not tidy adjacent code.
3. **No drive-by reformatting.** A formatting change is its own commit.
4. **Preserve conventions** already in the file, even if you would choose otherwise.
5. **Never edit generated files.** Fix the generator. Generated files carry a
   header saying so.
6. **Never weaken a test** to make a change pass.

### Comments

Explain **why**, never what. A comment restating the code is noise.

```python
# Wrong: increment the counter
# Right: bluetoothctl exits 0 even when the connection fails, so the
#        output must be checked as well as the status code.
```

---

## 6. Committing

### When

Commit at each **logically complete** step: one idea per commit, tests passing.

Commit when:
- A behaviour change is complete and tested.
- A refactor is complete and behaviour is unchanged.
- A document is coherent.

Do **not** commit:
- Work in progress that does not build.
- Several unrelated changes together.
- Formatting mixed with behaviour.

### Message format

[Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

| Type | Use |
|---|---|
| `feat` | A new capability |
| `fix` | A defect repaired |
| `docs` | Documentation only |
| `refactor` | Behaviour unchanged |
| `test` | Tests only |
| `perf` | Performance |
| `build` | Build system, dependencies |
| `ci` | Pipelines |
| `chore` | Maintenance with no src or test change |
| `revert` | Reverting a prior commit |

Rules for the subject line:

- Imperative mood: "add", not "added" or "adds".
- No capital first letter, no trailing full stop.
- 72 characters or fewer.
- Scope is the affected area: `fix(a2a):`, `docs(skills):`.

The body explains **why**, wrapped at 72 columns. Required whenever the reason
is not obvious from the subject.

Footers:

```
Fixes: #123
Refs: ADR-0019
BREAKING CHANGE: <what broke and what to do about it>
```

### Example

```
fix(a2a): resolve broker socket path at call time

DEFAULT_SOCKET was a plain string containing "{os.getuid()}", so the
placeholder was never substituted and the broker could not bind. Making
it an f-string alone was insufficient: serve() and listen() bound the
value as a default argument at import time.

Fixes: BUG-1
```

### Never

- No credential, token, or `.env` file in a commit.
- No commit directly to `main`.
- No amending or rebasing a commit that has been pushed.
- No `--no-verify`.

---

## 7. Pushing

**Push is deliberate and batched. Committing is not pushing.**

### When to push

| Trigger | Action |
|---|---|
| The user says "push" | Push now. |
| A branch is complete and green | Push, open a pull request. |
| **5 or more commits** accumulated on a branch | Push. |
| End of a working session | Push whatever is committed. |
| Anything urgent: a security fix | Push immediately. |

Between those points, commit freely and leave the work local. Pushing after
every commit produces noise, wastes CI, and makes history hard to read.

### Before pushing

```bash
make check          # must be green
git log --oneline origin/main..HEAD
```

Read your own commits back. Fix a bad message with an interactive rebase
**before** the push, never after.

### Never

- No force-push to a shared branch.
- No push to `main`. Every change arrives through a pull request.
- No push with a red gate.

---

## 8. Branches

```
<type>/<short-slug>
```

`feat/bluetooth-mcp`, `fix/a2a-socket-path`, `docs/adr-rewrite`,
`refactor/tools-layout`, `chore/pin-actions`.

Lowercase, hyphenated, under about 40 characters. One branch per work item.
Delete after merge.

`main` is protected: no direct pushes, no force-pushes, gate must pass.

---

## 9. Pull requests

### Title

Same format as a commit subject. The title becomes the squash-merge subject.

### Body

```markdown
## What
One or two sentences.

## Why
The problem this solves. Link the issue or ADR.

## How
Approach, and any alternative rejected.

## Verification
Commands run, with real output.

## Risk
What could break, and how to reverse it.
```

### Rules

- One work item per pull request. Under about 400 changed lines where possible.
- Draft while in progress; mark ready only when the gate is green.
- Squash-merge to `main`, so history is one commit per item.
- Never merge your own without review **unless** the repository is single-maintainer
  and the gate is green; say which applies.

---

## 10. Issues

Every non-trivial work item begins as an issue.

```markdown
## Problem
What is wrong or missing. Evidence, not opinion.

## Expected
What should happen instead.

## Scope
Repositories and files affected.

## Done when
Checklist a reviewer can verify.
```

### Labels

| Set | Values |
|---|---|
| Type | `type:bug`, `type:feat`, `type:docs`, `type:refactor`, `type:chore` |
| Priority | `p0` blocker, `p1` next, `p2` planned, `p3` someday |
| Area | `area:core`, `area:memory`, `area:docs`, `area:ci`, `area:desktop`, … |
| State | `blocked`, `needs-decision`, `good-first-issue` |

Exactly one type and one priority. `p0` means work stops for it.

---

## 11. Milestones, projects, and views

**Milestones** are dated and represent a shippable increment: `v0.2.0 — desktop
control`. An issue belongs to at most one. An empty or perpetually slipping
milestone is closed, not extended.

**Projects** (one board, fleet-wide) with columns:

```
Backlog → Ready → In progress → In review → Done
```

- **Ready** means specified enough to start without asking.
- **In progress** is limited to **two items per worker**. Finish before starting.
- Moving to **In review** requires a green gate.

**Views**: *By priority* (triage), *By area* (ownership), *By milestone*
(release readiness), *Blocked* (needs a decision).

---

## 12. Versions, tags, releases

[Semantic Versioning](https://semver.org/): `MAJOR.MINOR.PATCH`.

| Increment | When |
|---|---|
| MAJOR | A breaking change to a public interface, a tool name, or a config schema |
| MINOR | A capability added, backwards compatible |
| PATCH | A fix, backwards compatible |

Pre-1.0 components may break on MINOR; say so in the changelog.

**Tags** are annotated and prefixed: `v0.2.0`. One tag per component release.

```bash
git tag -a v0.2.0 -m "shesh-core 0.2.0: desktop device control"
git push origin v0.2.0
```

**Release checklist**

1. `CHANGELOG.md` updated under a version heading with a date.
2. Version bumped in `pyproject.toml` or `Cargo.toml`.
3. Gate green on `main`.
4. Tag created and pushed.
5. Release notes generated from the changelog.
6. Manifest updated in `shesh-ecosystem` if the component version moved.

Never re-point a published tag. Ship a new patch instead.

---

## 13. Changelog

[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Sections: `Added`,
`Changed`, `Deprecated`, `Removed`, `Fixed`, `Security`.

Write for someone deciding whether to upgrade. "Fixed a bug" is useless;
"screenshots were written as invalid PNGs" is not.

Every user-visible change lands in `Unreleased` in the same commit.

---

## 14. Maintenance

| Cadence | Task |
|---|---|
| Every change | Gate green; changelog updated |
| Weekly | Dependency updates reviewed; failed CI triaged |
| Monthly | `make sync-check`; stale branches deleted; `p0`/`p1` reviewed |
| Quarterly | Upstream forks rebased; ADRs reviewed for supersession; archive swept |

Automated and enforced, so none of it depends on memory:

| Tool | Keeps in sync |
|---|---|
| `tools/handoff.py` | `STATE.md` |
| `tools/sync_fleet.py` | Boilerplate, workflows, action pins |
| `tools/generate_components.py` | Component catalogue from the manifest |
| `tools/check_docs.py` | Documentation style and links |
| `test_skills_spec.py` | Skill conformance |

Editing generated content by hand is a defect in the generator.

---

## 15. Stop and ask

- The gate fails and the cause is not obvious.
- The task needs a credential, a purchase, or an irreversible action.
- The task requires deleting data or rewriting history.
- Three attempts have not landed a change.
- Two documents disagree and neither is clearly current.
- The change would span product and factory.

**Stopping and reporting is a success. Guessing is not.**

---

## 16. Never

- No credential in a file, commit, log, or message.
- No force-push, no rewriting published history, no pushing to `main`.
- No weakening a test, gate, or policy to make something pass.
- No writing to `~/.ssh`, `~/.gnupg`, vaults, or employer directories.
- No reporting unrun tests as passing.
- No claiming a component does something without reading its code.
- No volatile counts in documentation.
