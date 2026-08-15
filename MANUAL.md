# MANUAL.md

Step-by-step procedure for working on the Shesh fleet. Written for an agent or
a person arriving with no prior context.

Read this before touching anything. It exists because the mistakes recorded in
[§9](#9-known-failure-modes) were expensive, and every one of them was
avoidable by following a step already known.

Companion documents:

| File | Purpose |
|---|---|
| [FACTORY.md](FACTORY.md) | The working agreement: input, output, commits, pushes, releases |
| [STEER.md](STEER.md) | The single next action, generated |
| [QUEUE.md](QUEUE.md) | The work queue |
| [`shesh-ecosystem/HANDOFF.md`](https://github.com/gaganjainse/shesh-ecosystem/blob/main/HANDOFF.md) | Where everything lives |
| [`shesh-ecosystem/AGENTS.md`](https://github.com/gaganjainse/shesh-ecosystem/blob/main/AGENTS.md) | Conventions and judgment boundaries |

---

## 1. Start a session

Run these in order. Do not skip a step because it "looks fine".

```bash
cd <fleet-root>

# 1. Credentials. Never ask the operator to paste a token into a conversation:
#    a pasted token is exposed permanently in the transcript.
export SHESH_PAT_PASSWORD='<store password>'
python3 shesh-workspace/tools/token.py check

# 2. What to do next.
python3 shesh-workspace/tools/steer.py show

# 3. What state the fleet is in.
cat shesh-ecosystem/STATE.md

# 4. Prove the gate is green BEFORE you change anything.
cd shesh-ecosystem && SHESH_SRC=$(cd .. && pwd) make check
```

**A red gate on arrival is not yours to build on.** Fix it or report it first;
otherwise you cannot tell which failure is yours.

---

## 2. Claim work

```bash
python3 shesh-workspace/tools/steer.py claim <id> --agent "<your-name>"
```

Claiming is advisory but prevents two sessions doing the same work. A claim
idle beyond eight hours is reclaimable, because sessions end without warning.

If the queue is empty, ask. Do not invent work.

---

## 3. Decide where the change belongs

| Change | Repository |
|---|---|
| A tool server or governance primitive | `shesh-core` |
| Memory, orchestration, refinement, phone, routing | The matching service repository |
| Component versions, channels, gates | `shesh-ecosystem` |
| Architecture, procedures, reference, policy | `shesh-docs` |
| A skill served to agents | `shesh-skills` |
| Session tooling, credential helpers, parallel agents | `shesh-workspace` |
| A superseded record | `shesh-docs-archive` |

**The product-and-factory test is what a user installs, not which directory a
file sits in.** A gate that resolves the manifest is composition tooling and
belongs in `shesh-ecosystem`, even though it never reaches a machine. Getting
this wrong broke five gates once already; see [§9](#9-known-failure-modes).

Do not span repositories in one change. Sequence them and state the order.

---

## 4. Make the change

1. **Read every file you intend to change, in full.** Not a grep of the
   function name.
2. **State the plan** for anything touching more than about three files: which
   files, what approach, what could break.
3. **Smallest change** that completes the item. No drive-by reformatting.
4. **Never edit a generated file.** They carry a header saying so. Fix the
   generator.
5. **Add a test with a fix.** It must fail against the old code.
6. **Never weaken a test, a gate, or a policy** to make something pass.

### If you move or rename anything

This is the highest-risk operation in the fleet. Before committing:

```bash
# Every path referenced by a gate must still resolve.
cd shesh-ecosystem
for f in $(grep -ohE '(tools|scripts)/[a-z_]+\.(py|sh)' \
           .github/workflows/*.yml Makefile | sort -u); do
  [ -f "$f" ] || echo "MISSING $f"
done

python3 tools/linkcheck.py docs        # documentation links
python3 tools/depgraph.py --check docs/architecture/dependency-graph.md
python3 tools/docs_index.py --check
```

A rename that passes locally can still break CI when a tool derives its input
from what happens to be checked out. See [§9](#9-known-failure-modes).

---

## 5. Commit

```bash
git checkout -b <type>/<slug>          # never work on main
git add -A -- <specific paths>         # not a blind git add -A
git commit                             # the hook validates the message
```

Format is enforced by `commit_policy.py`:

```
<type>(<scope>): <subject>      # imperative, lowercase, no full stop, <=72
                                # blank line
<body wrapped at 72>            # why, not what
```

Types: `feat` `fix` `docs` `refactor` `test` `perf` `build` `ci` `chore` `revert`.

The hook also rejects a message containing a credential. If it does, the token
is compromised: rotate it, do not simply reword the message.

---

## 6. Verify before pushing

**No red reaches `main`. This is not negotiable.**

```bash
# Every component you touched.
cd <repo> && python3 -m pytest tests/ -q

# The fleet gate.
cd shesh-ecosystem && SHESH_SRC=$(cd .. && pwd) make check

# Documentation, if you touched any.
cd shesh-docs && python3 tools/check_docs.py && mdbook build
```

`make check` runs lint, tests, boilerplate drift, the journal, and the queue.
All of it must be green.

---

## 7. Push

Pushing is deliberate and batched. Committing is not pushing.

| Trigger | Action |
|---|---|
| The operator says "push" | Push now |
| Five or more commits on a branch | Push |
| A branch is complete and green | Push, open a pull request |
| End of session | Push what is committed |
| A security fix | Push immediately |

```bash
# The remote URL comes from the encrypted store, never from a pasted token.
REMOTE=$(python3 shesh-workspace/tools/token.py remote <repo>)
SHESH_PUSH_NOW=1 git push "$REMOTE" "HEAD:refs/heads/<branch>"
```

Most repositories carry a GitHub ruleset requiring a pull request. That is
deliberate. **Do not attempt to bypass it.** Open the pull request, wait for
the checks, and merge only when every one is green.

`SHESH_ALLOW_MAIN=1` exists for the single-maintainer case where the gate is
green and there is no second reviewer. It is a record that an exception was
made, not permission to forget the rule.

### Watch the checks

```bash
gh pr checks <number> --repo gaganjainse/<repo>
```

A `cancelled` result is not a failure: a matrix leg aborts when a sibling
fails. Find the leg that actually failed before investigating anything else.

---

## 8. Close the session

```bash
python3 shesh-workspace/tools/steer.py done <id>       # or: release <id>
python3 shesh-workspace/tools/journal.py record \
  --query "<what was asked>" --answer "<what was done, including what failed>"
python3 shesh-workspace/tools/journal.py sync
```

The journal is the factory's memory. A session that records nothing forces the
next one to re-derive everything. Record failures as prominently as successes.

Leave the tree either committed on a branch or clean. Never leave uncommitted
work with no note: the next session cannot tell an experiment from an
unfinished fix.

---

## 9. Known failure modes

Every entry cost real time. Read them; they repeat.

### A tool that fails silently looks maintained

`live_update.py` resolved paths that a reorganisation had moved and returned
quietly when they were missing. The decision log went unwritten for two
sessions and nothing complained.

**Rule:** a tool exits non-zero when its target is missing. Never `return` on
a missing path. `journal.py` and `steer.py` both have a `--check` mode wired
into the gate for this reason.

### Moving a file breaks the gate that calls it

The product-and-factory split was applied too literally. `sign_artifacts`,
`export_traces_otlp`, `proofread`, `verify_worktrees`, and `docs_index` were
moved to `shesh-workspace`, which left five gates calling scripts that were no
longer there.

**Rule:** before moving anything, grep every workflow and Makefile for its
name. The check in [§4](#4-make-the-change) does this.

### A generator whose input depends on its own output

`depgraph.py` derived its clone list partly from what was already checked out.
CI cloned a subset, generated a smaller graph, and reported the committed
graph as stale on every run — unfixable by regenerating.

**Rule:** a generated artefact is a function of committed sources only, never
of the working directory. Verify by generating from a minimal checkout and a
full one and diffing.

### `|| true` hides the failure you needed to see

Ten instances in `shesh-desktop`. One masked a CI step so a script that would
not run still reported green. Removing the mask surfaced a genuine bug.

**Rule:** handle the specific expected failure; never blanket-suppress. If a
unit may be absent, match on "not loaded" and report anything else.

### `allowed-tools` grants, it does not restrict

A grant was added to the always-active `safety-governance` skill and described
as making it read-only. It did the opposite: it pre-approved three tools in
every session.

**Rule:** `allowed-tools` widens permissions. Restriction is `disallowed-tools`
or the policy engine. A safety skill carries no grant at all.

### Documenting behaviour that does not exist

A claim was written that `shesh-skills` served its library over the Model
Context Protocol. Nothing read the directory; it was not even packaged.

**Rule:** never write "component X does Y" without reading the code. The
documentation linter cannot catch this — only a person or a test can.

### A policy nobody scheduled is not a policy

The fleet declared an adoption policy and a register of 21 upstreams, but no
workflow ever read it, and the tracker parsed a different table name than the
register used. Nothing was adopted for weeks.

**Rule:** a policy needs a trigger. If it is not on a schedule or in a gate, it
will not happen. `upstream-watch.yml` now runs weekly.

### A credential in a chat is burned

Tokens were pasted into conversation twice and had to be rotated both times,
while an encrypted store already existed and went unused.

**Rule:** use `token.py`. Never ask for a paste.

### A standardiser can standardise a repository into breaking

`asyncio_mode` and `pytest-asyncio` were added to every Python component for
uniformity. Only one has async tests. CI installs from the shared pipeline
rather than the dev extra, so pytest met an unknown config key and aborted
during collection with an internal error, not a readable message.

**Rule:** uniformity means the same *rules*, not the same *file contents*. A
setting only belongs where the thing it configures exists. After a fleet-wide
edit, run the gate for at least one repository of each shape.

### A stale pin fails before any job starts

`shesh-skills` pinned an older revision of the reusable workflow than the rest
of the fleet. The run failed with no jobs, no logs, and no check-runs, so every
attempt to read the failure returned nothing.

**Rule:** an empty job list means the workflow file could not be resolved, not
that the tests failed. Compare the pin against a repository that passes.

### An unarchived repository runs CI again

Sixteen repositories superseded by `shesh-core` still held their source.
Archived, that was inert. Unarchived, their pipelines ran against code nobody
maintains and every one went red.

**Rule:** a superseded repository becomes a tombstone — history and README
kept, source removed, and a CI job that asserts it stays inert. Two copies of
a module always drift.

### "Green on main" is not "the PR is green"

I told the operator three PRs were ready because their target branches were
green. The PRs themselves were red: the fix had not landed, so main was green
*because* the change was still outside it.

**Rule:** judge a PR by the checks on its head SHA, never by the state of the
branch it targets. `gh pr checks <n>` or the check-runs API on the head commit.

### A stale check-run looks like a live failure

A `PR Validation` failure kept reporting a merge conflict that `git merge` and
the API both said did not exist. The check-run was from before the branch was
rebased and had never re-run.

**Rule:** compare the check-run timestamp against the head commit. If it
predates the push, force a fresh run with an empty commit rather than debugging
the old output.

### A shallow clone has no merge base

The same check then failed for real: `git merge-tree --write-tree HEAD
origin/main` returns non-zero when the shallow clone shares no history with the
base, and the step read that as a conflict.

**Rule:** deepen the fetch before comparing branches in CI, and match on the
`CONFLICT` marker rather than an exit code that means several things.

### Rewriting a pin to a tag is a supply-chain regression

`sync_fleet.py` normalised 86 pinned SHAs down to `actions/checkout@v4`. A tag
is mutable, so this handed control of the action to whoever can move it. The
zizmor `unpinned-uses` audit caught it and failed every workflow that ran it.

**Rule:** every action pin is a 40-character SHA with a comment naming the
release. `sync_fleet.py` now refuses to write anything else.

---

## 10. Adopting from upstream

The fleet prefers a maintained upstream over building
([ADR-0018](https://github.com/gaganjainse/shesh-docs/blob/main/src/governance/adr/0018-adopt-vs-build.md)).

```bash
cd shesh-ecosystem
python3 tools/assimilate.py --report     # what moved, and each licence verdict
python3 tools/assimilate.py --queue      # turn advances into work items
```

Before adopting anything:

1. **Licence.** Must combine with GPL-3.0-or-later. AGPL and SSPL may be
   reached only across a process boundary, never linked. The tool reports a
   verdict; an undeclared licence is not permission.
2. **Boundary.** Wrap it behind the policy engine. Never let a client talk to
   an adopted server directly, or the guard is bypassed.
3. **Record.** Write an ADR stating what was adopted, what was rejected in the
   same review, and why. [ADR-0020](https://github.com/gaganjainse/shesh-docs/blob/main/src/governance/adr/0020-adopt-computer-use-linux.md)
   is the worked example.
4. **Pin.** Add it to the manifest so the version is tracked.

Do not adopt a capability the fleet has no use for. The goal is a working
system, not a large inventory.

---

## 11. Keeping this manual current

When something breaks in a way that was avoidable, add it to
[§9](#9-known-failure-modes) in the same change that fixes it. One paragraph:
what happened, then the rule that prevents it.

A failure mode that is fixed but unrecorded will recur, because the next
session has no memory of it.

```bash
python3 shesh-workspace/tools/journal.py record \
  --query "..." --answer "... Added a failure mode to MANUAL.md §9."
```
