# Decision journal

Every instruction and the decision taken in response, newest last. Appended
verbatim, never summarised: a summary loses the reasoning that makes an old
decision reviewable.

This is the factory's memory. When a session ends and another begins, this is
what explains why the code looks the way it does.

Maintained by `tools/journal.py`. Do not edit by hand.


---

## 2026-08-15

**Asked**

Rewrite all documentation professionally and uniformly; audit the fleet.

**Done**

Cloned 30 repos. Restructured shesh-docs from 124 chapters across 12 overlapping parts into a Diataxis layout. Removed 800+ style violations: 364 first-person, 74 acquisition metaphors, 64 volatile counts, 59 personal paths, 145 TODO markers, 78 emoji headings. Found the install guide was broken: it instructed pipx install of 15 repos that ADR-0019 had consolidated into shesh-core and archived. Added STYLEGUIDE.md and check_docs.py to enforce it.

<sub>Recorded 2026-08-15T10:22:45+00:00</sub>

---

## 2026-08-15

**Asked**

Is a 124-chapter book overkill?

**Done**

Yes, and measurement showed where. Twelve how-to pages were 100 percent verbatim duplicates of the verification checklist, 77 of 77 items. Deleted after proving zero information loss. Merged sub-200-word stubs, extracted History to shesh-docs-archive and contributor tooling to shesh-workspace. 124 to 71 chapters, 59 percent smaller.

<sub>Recorded 2026-08-15T10:22:45+00:00</sub>

---

## 2026-08-15

**Asked**

Are the skills built to the Anthropic standard? Also fix safety-governance allowed-tools.

**Done**

They were not. Files were skills/name.md rather than skills/name/SKILL.md, with no allowed-tools and no licence. Rebuilt to the Agent Skills specification. Also corrected my own earlier error: I had set allowed-tools on safety-governance and called it read-only. That field GRANTS permission without prompting, it does not restrict. On an always-active skill it widened every session. It now carries no grant at all and declares its enforcement dependency on shesh-audit. I had also written a false claim that shesh-skills served the library over MCP; nothing read the directory. Implemented the capability rather than deleting the sentence.

<sub>Recorded 2026-08-15T10:22:45+00:00</sub>

---

## 2026-08-15

**Asked**

What other agent file types are needed? Build hundreds of skills for whole-computer control.

**Done**

Researched AGENTS.md, SOUL.md, SPEC.md, llms.txt, CLAUDE.md. Adopted AGENTS.md as canonical in shesh-ecosystem with pointers in 13 repos, plus a thin CLAUDE.md import. Rejected SOUL.md, llms.txt, SPEC.md with reasons recorded in reference/agent-files.md. Built 37 skills, not hundreds: shesh-core exposes 60 MCP tools, and a skill naming an absent tool fails at the first call. Remaining capabilities catalogued in GAPS.md.

<sub>Recorded 2026-08-15T10:22:45+00:00</sub>

---

## 2026-08-15

**Asked**

Fleet uniformity, a working factory, folder-level reorganisation, rewrite ADRs, commit in batches then push.

**Done**

Wrote FACTORY.md covering input, output, documents, edits, commits, pushes, branches, PRs, issues, labels, milestones, projects, versions, releases, maintenance and stop conditions. Enforced by commit_policy.py as commit-msg and pre-push hooks in 30 repos, including a five-commit push batch. Moved 29 factory files out of shesh-ecosystem. Rewrote 19 ADRs to one format, content unchanged. Fixed 4 critical audit bugs with regression tests. Added shesh_desktop_ctl with 19 tools. Committed in batches; 4 repos pushed to main, 10 opened as PRs because GitHub rulesets require review.

<sub>Recorded 2026-08-15T10:22:45+00:00</sub>

---

## 2026-08-15

**Asked**

What is still undone from my earlier instructions, and are you maintaining the live-update documents?

**Done**

Audited rather than recalled. Found two genuine failures: live_update.py had silently stopped working after the reorganisation moved its target paths, so the decision log and TODO stamp had not been written for two sessions; and repository naming had been deferred twice. Fixed both. Replaced live_update.py with journal.py, which fails loudly on a missing target and is wired into the gate. Renamed SheshAOS to shesh-aos and shesha-kernel to shesh-kernel. Adopted computer-use-linux under ADR-0020 with a guarded proxy. Wrote OUTSTANDING.md listing every instruction against its evidence.

<sub>Recorded 2026-08-15T10:29:21+00:00</sub>

---

## 2026-08-15

**Asked**

Check the system is flowing, the dependency graph and prior artifacts work, whether queue and steer artifacts exist for agents without them, and whether ADRs and the mdBook are maintained. Also PR #19 and #51 are failing.

**Done**

Audited every artifact. Found and fixed six failures, all caused by my own kebab-case rename and the factory move. depgraph pointed at DEPENDENCY_GRAPH.md and derived its clone list partly from what was already checked out, so CI generated a smaller graph and reported staleness on every run; the manifest is now the only input and output is byte-identical between a CI-shaped and a full checkout. The book-mirror gate was removed with book_build.py: all 74 destinations it enforced no longer exist since single-sourcing replaced copy-paste. Nine documentation links repaired. sign_artifacts, export_traces_otlp, proofread, verify_worktrees and docs_index were wrongly moved to the factory and are back. Ten silent-failure findings in shesh-desktop fixed, including a CI step that masked --help failures; the fix surfaced a genuine root-refusal bug. Added QUEUE.md and STEER.md with advisory claiming for agents that have no orchestration, wired into the gate. All five PRs merged; 11 of 11 checks green.

<sub>Recorded 2026-08-15T11:20:07+00:00</sub>
