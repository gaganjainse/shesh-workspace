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

Every failure that cost time is a row in
[`failures/register.toml`](failures/register.toml), not a paragraph here. Prose
is read once and forgotten; a row can be counted, queried, and attached to a
detector that runs on every build.

```bash
python3 tools/guard.py --check     # run every detector; the gate does this
python3 tools/guard.py --list      # the register as a table
python3 tools/guard.py --show F014 # one failure in full
python3 tools/guard.py --gaps      # rows that still rely on a person
python3 tools/guard.py --stats     # coverage, and which rules are not working
```

A guard firing does not mean something new is wrong. It means a mistake already
made is being repeated, and the row tells you what was learned the first time.

### When something breaks

Add the row in the same change that fixes it:

```bash
python3 tools/guard.py --new       # prints the next id and a template
```

Write a guard unless the mechanism is genuinely undetectable. Prefer a narrow
guard that catches the specific mechanism over a broad one that catches
nothing: a guard with false positives gets ignored, and an ignored guard is
worse than none because it looks like cover.

If the same failure recurs, increment `recurrence` rather than adding a row.
A count above one means the rule is not working and the guard needs to be
stronger — `--stats` reports those separately for that reason.

### What the register currently holds

| | |
|---|---|
| Recorded failures | 15 |
| Guarded, cannot silently return | 13 |
| Relying on a person | 2 |

The two unguarded rules are documenting behaviour that does not exist, and
mistaking a stale check-run for a live failure. Both need a person, for now;
`--gaps` keeps them visible rather than letting them fade.

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

When something breaks in a way that was avoidable, add a row to the failure
register in the same change that fixes it, and write a guard:

```bash
python3 tools/guard.py --new
```

A failure that is fixed but unrecorded will recur, because the next session has
no memory of it. A failure that is recorded but unguarded relies on someone
reading this file at the right moment, which is a weaker guarantee than a
build that fails.

Then record the session:

```bash
python3 tools/journal.py record --query "..." --answer "..."
```

The register is the durable memory; the journal is the narrative. Both are
checked by `make check`, so neither can quietly fall behind.
