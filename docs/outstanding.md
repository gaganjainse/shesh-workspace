# Outstanding work

Audit of every instruction given in this session against what was delivered.
Written because "did you do X" deserves a checkable answer, not recollection.

Last verified: 2026-08-15.

## Delivered

| Asked | Delivered | Evidence |
|---|---|---|
| Rules for where files go and how to continue in a new session | `HANDOFF.md`, `AGENTS.md` in 14 repositories, generated `STATE.md` | `make check` includes `sync-check` |
| Keep product and factory separate | 29 factory files moved out of `shesh-ecosystem`; verified mechanically | No session, credential, or swarm tooling in any product repository |
| Standardise repository names | `SheshAOS` → `shesh-aos`, `shesha-kernel` → `shesh-kernel` | GitHub redirects the old URLs; 46 files updated |
| Standardise filenames | 68 SCREAMING_SNAKE files renamed to kebab-case | 0 remaining in `shesh-ecosystem/docs` |
| Folder and file level reorganisation | Factory extracted, root tidied, book restructured by document type | 124 → 72 chapters |
| Automate everything | `journal.py`, `handoff.py`, `sync_fleet.py`, `factory_sync.py`, `generate_components.py`, `check_docs.py` — all with `--check` in the gate | `GATE OK` |
| Uniformity across agents | `FACTORY.md`, 16 sections, enforced by `commit_policy.py` hooks in 30 repositories | Rejected five of my own commits during this work |
| Batch commits, push at once | Committed in batches; pushed to `main` where permitted, PRs where rulesets require review | 9 repositories on `main`, 4 PRs open |
| Rewrite ADRs, format only | 20 records, uniform header and sections, consequences split | Content unchanged |
| Bluetooth, Wi-Fi, brightness, clipboard, session control | `shesh_desktop_ctl`, 19 tools, 7 skills | 46 tests |
| Adopt maintained upstreams | ADR-0020 adopts `computer-use-linux` (MIT), proxied through the guard | 39 tests |
| Agent file conventions | `AGENTS.md` and `CLAUDE.md` adopted; `SOUL.md`, `SPEC.md`, `llms.txt` rejected with reasons | `reference/agent-files.md` |
| Fix `safety-governance` grant | Grant removed entirely; the field pre-approves rather than restricts | Two tests enforce it |
| Live-update documents | `journal.py` replaces `live_update.py`, which had silently stopped working | `journal check` in the gate |

## Open

### Awaiting review

Several repositories carry GitHub rulesets requiring a pull request. The work is
pushed and ready:

- [shesh-ecosystem#51](https://github.com/gaganjainse/shesh-ecosystem/pull/51)
- [shesh-docs#3](https://github.com/gaganjainse/shesh-docs/pull/3)
- [shesh-core#4](https://github.com/gaganjainse/shesh-core/pull/4)
- [shesh-aos#19](https://github.com/gaganjainse/shesh-aos/pull/19)

Seventeen archived repositories hold one local commit each, applying the rename
and the boilerplate. They are read-only by design
([ADR-0019](https://github.com/gaganjainse/shesh-docs/blob/main/src/governance/adr/0019-shesh-core-monorepo.md)),
so the commits stay local unless a repository is deliberately unarchived.

### Not done

| Item | Why |
|---|---|
| Hundreds of skills | 38 exist, one per real tool. A skill naming a tool the fleet does not expose fails at the first call and misleads the agent into believing the capability exists. Remaining capabilities are registered in `GAPS.md` with the interface each needs. |
| `mcp-linux-desktop`, `hyprmcp` | Assessed and rejected in ADR-0020. The first overlaps `shesh_desktop_ctl` and had no clearly declared licence; the second is narrower than the adopted option. |
| `anthropics/skills` document handling | Not adopted. The PDF, DOCX, XLSX, and PPTX skills assume a code-execution sandbox the fleet does not run. Adopting them needs a container path first. |
| Display and monitor control | Registered in `GAPS.md`. Needs `wlr-randr` or `hyprctl monitors` tooling before a skill can name it. |
| Verification on hardware | Every page reads `verified: 2026-08-15`, which is a source-level check. GPU, audio, display, phone, and voice procedures need confirming on the reference machine. |

## Standing risk

The tokens used during this session were shared in conversation. They should be
revoked. Remotes carry no embedded credentials; the only copies are in chat
history.
