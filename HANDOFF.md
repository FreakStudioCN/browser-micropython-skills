# Handoff — Browser MicroPython Skills content migration (方案 1)

## Goal

Make the 27 `*-browser/SKILL.md` skills **capability-equivalent** to the upstream
`FreakStudioCN/MicroPython_Skills`, not just structurally equivalent. The skills had been migrated to the
Blockless contract (5 primitives) but were **auto-generated thin stubs (~70 lines)** that had dropped the entire
upstream **domain payload** (P0–P2 rule checklists, 13-section README templates, optimization tables, code
templates, command catalogs). This work restores that content via **clone-then-modify**: each browser skill
starts from a copy of its content-rich upstream `SKILL.md`, keeps every rule verbatim, and swaps **only the
execution layer** to Blockless primitives (`file_operation` / `device_command` / `browser_validate` /
`approval_request` / `phase_complete`). It also encodes the upstream **two-spine / three-tier** structure as data.

Target repo: `C:\Users\Haipeng Wu\Desktop\blockless\browser-micropython-skills-new` (remote `FreakStudioCN/browser-micropython-skills`, branch `main`).
Reference of truth (the 1:1 source — confirmed by the user): `FreakStudioCN/MicroPython_Skills` = on disk `C:\Users\Haipeng Wu\Desktop\blockless\MicroPython_Skills_upstream` (canonical, has the remote; also vendored at `cursor_for_hardware/third_party/MicroPython_Skills` — **never edit third_party/**). The no-remote clone `…/browser-micropython-skills` was the original content source (redundant now).
Base commit `bfb79a1`. **Work is COMMITTED + PUSHED**: `1ad02b6` (migration + orchestration metadata + host-execution scrub) and `5fbaf2a` (1:1 audit — restored dropped domain contracts in 7 skills). Working tree clean.

## Post-handoff correction (2026-06-28) — one skill was only half-migrated

The "COMPLETE and verified" claim below was **overstated**. A follow-up audit found `webserial-live-session-browser/SKILL.md`
was a near-verbatim copy of upstream `mpremote-live-session` whose **host-PTY/subprocess payload survived** the migration
(`os.fork`, `pty.openpty`, `os.execvp("mpremote", …)`, `subprocess.Popen(["mpremote", …])`) — code that cannot run in the
browser target at all, while the skill's own header prose claimed the device CLI/PTY was "replaced by `device_command` only".

**Root cause of the miss:** the leak gate token was `"mpremote "` (trailing space); the leak was `"mpremote"` (quote, no
space), and `os.fork`/`pty.openpty`/`subprocess.Popen` were not forbidden at all. Two Codex rounds + the narrow scan all
passed it.

**Fixed (round 1 — webserial):** (1) rewrote the live-session host-PTY/subprocess sections into `device_command`
persistent-session prose (open/send/read/return-via-`phase_complete`-evidence/close) — kept the asyncio Ctrl+C rule,
resume semantics, aiorepl vs raw_repl, stall detection; (2) cleaned two host-shell loops in `webserial-file-transfer-browser`
(`for f in *.py; do …`, `mkdir -p backup/data` + `awk`) to abstract device_command / project-store form; (3) fixed a
"persistent PTY session" cross-ref in `webserial-device-interaction-browser`; (4) broadened the forbidden gate
(`os.fork`/`os.execvp`/`pty.openpty`/`subprocess.popen`/`pexpect`/quoted `"mpremote"`).

**Round 2 — Codex confirmation pass caught a SECOND host-execution class the gate AND a manual `python3 ` sweep both
missed: bare host `python` invocations.** Five more skills shelled out to host CPython, each mapped to a primitive the
skill *already declared*:
- `upy-diagram-browser` / `upy-wiring-browser` — `cd {project_dir} && python -c "…"` rewriting `project-manifest.json`
  → `file_operation` read/merge/write.
- `upy-pkg-guide-browser` — `python "C:/Users/Administrator/.claude/skills/…/search_awesome.py"` (host binary + hardcoded
  host path) → `browser_validate (awesome_micropython_search)` (its own Step-1 primitive).
- `upy-analyze-browser` (×3) — `python {skill_dir}/scripts/init_manifest.py …` validation → `browser_validate (manifest)`
  / `(manifest_phase)` (its own Step-5 primitives).
- `upy-simulate-browser` (×3) — raw `python test/pc/sim_main.py …` run/re-run commands → `browser_validate (simulate_run)`
  (its own Step-5 primitive).

The gate was hardened with a **regex** (not another substring token):
`(?<![a-z])python[0-9]? +(?:-|/|\.|\{|"|'|[a-z]:[\\/]|[\w.]+/|[\w.]+\.py)` — catches `python -c` / `python <path>` /
`python {tmpl}` / `python "path"` / bare `python C:/x.py` / bare `python x.py`, while excluding `micropython`, `cpython`,
the `python_syntax` validate-kind, and "Python 3.11" prose. **Codex confirmed the round-1 live-session rewrite is clean**
(lines 17/70/105/112 are prohibitive prose, not executable host actions; declared primitive set consistent; no undeclared
`file_operation`).

**Round 3 — a third independent Codex pass confirmed all 5 round-2 mappings are faithful and found two small residues**, both
fixed: (i) `upy-analyze-browser` 权限策略 still listed "运行白名单脚本 `scripts/init_manifest.py`" as a permitted action and a
`structured_errors` example used `"source": "init_manifest.py"` → both repointed to `browser_validate` (`manifest`); (ii) the
host-python regex had a false-negative on a bare unquoted `python C:/x.py` (drive letter) and bare `python x.py` (no
separator) → added the `[a-z]:[\\/]` and `[\w.]+\.py` branches. No other host-execution found in any of the 27 skills.
`pytest` → 42 passed; original leak scan + host-spawn/host-python regex scans all empty; fidelity still 17.

**Deferred (design question, NOT a leak):** `upy-simulate-browser` still *generates* sim code that imports host
`threading` / `rich` (terminal dashboard) / `tkinter` (GUI). That is generated-output guidance whose correctness depends on
what runtime the `browser_validate (simulate_run)` **provider** actually offers (terminal? headless? browser canvas?) — and
provider implementations are explicitly out of scope this pass (see Next Steps #5). Resolve the visualization story when the
`simulate_run` provider is built; left as-is intentionally.

## 1:1 capability audit (2026-06-28, round 4) — restored dropped domain contracts; COMMITTED + PUSHED (`5fbaf2a`)

The user asked to re-scan all 27 browser skills **one-by-one against the reference of truth `FreakStudioCN/MicroPython_Skills`**
(`MicroPython_Skills_upstream/`) and fix any skill that dropped domain content during migration (execution-only swap; the
upstream is "correct", ours must mirror it). Method: a line-count coverage scan flagged the 2 dramatically-thin skills, then a
**comprehensive Codex 1:1 audit across all 27 pairs** found the rest. **7 skills had over-thinned domain knowledge** — host
mechanics were cut correctly, but browser-relevant domain *contracts* went with them. All restored (execution still on the 5
primitives), **20 confirmed already-equivalent**:

- `review-browser` — Domain(12)/Severity(3, was wrongly "blocking/non-blocking")/Component(8) taxonomies + verdict types
  (confirmed/partially_valid/false_positive/inconclusive) + finding format + data scope.
- `upy-flash-mpy-firmware-browser` — 板卡事实 firmware-resolution field-priority table + "don't trust cached `latest_version` /
  don't build URL from `display_name`/`board_id`" rules.
- `upy-deploy-browser` — deployment-strategy taxonomy (`upload_only`/`clean_then_upload`/`erase_then_upload`) + destructive
  approval gates (`confirm_clean`/`confirm_erase`/`run_device_tests`) + 3-level verdicts incl `PASS_WITH_WARNINGS` (empty
  serial ≠ FAIL) + forbidden-artifact rules + error→cause table + structured `error_context` handoff.
- `upy-select-hw-browser` — board-facts source-of-truth + MCU candidate ranking + `restricted_gpio` severity table +
  `pinout[].type` enum + pinout field table + `pin_decisions`/`deviation`/`reason_code` model + board_unavailable/pin_plan_review gates.
- `upy-generate-browser` — supplement-routing + cloud/API integration safety (no real tokens in code) + `doc_evidence` +
  `runtime_dependencies` + production `deploy_plan` (source_only/upload_exclude) + partial/failed (retryable) judgment.
- `upy-analyze-browser` — driver-source classification guardrails (builtin_runtime vs micropython_lib vs upypi priority;
  `none`/`local` rules; decompose device-families) + minimum manifest-content delivery fields.
- `upy-scaffold-browser` — `scaffold_config` item_groups + module-id→output mapping + scheduler rec rules + invalid combos +
  `Scheduler` timer_id port rules + GPIO-direction-from-pinout + startup fatal guard + final file-manifest contract.

`pytest` → **42 passed**; host-execution / host-python regex scans empty. The gate caught my own one over-restoration (a
`.flake8` host-lint rule in scaffold) → removed (browser lint is `browser_validate (python_syntax/scaffold_contract)`, not host flake8).

## Current Progress — migration COMPLETE, committed + pushed

All 27 skills migrated, cross-cutting metadata added, host-execution scrubbed (rounds 1-3), 1:1 domain audit done (round 4).

- **27/27 `*-browser/SKILL.md`** carry full upstream domain content with execution swapped. Fidelity: skills
  with rule fingerprints (`P0`/`ISR`/`__slots__`/`docstring`/`viper`/`memoryview`) rose **0 → 17**; total
  browser SKILL.md lines **~1,900 → 9,242**.
- **`docs/reference/`** holds 3 bundled upstream guides (spec summary 2328, perf 1025, memory 1195 lines); the
  norm-driver/opt/slim skills cite them by relative path.
- **Orchestration metadata** on all 27 manifest entries (`tier`/`spine`/`phase`/`orchestrates`/`calls`), exposed
  via `SkillCatalog.orchestration` in `runtime.py` + `cli catalog`, documented in `docs/skill-orchestration-map.md`,
  guarded by `tests/test_skill_orchestration.py`. README updated.
- **Earlier fail-fast guard** (`reference_mode` in `validation.py`) is intact and still tested.
- **Codex round 1** (7 MUST-FIX) and **round 2** (4 PARTIAL) findings ALL fixed except #7 (deferred, see below).

Verification (run from the target repo): `python -m pytest tests -q` → **42 passed**;
`python -m browser_skill_contract.cli dry-run-workflow --project-name blink` → `status: success`;
`cli catalog` → exit 0; the broadened forbidden gate → **zero leaks**.

## What Worked

- **clone-then-modify via `cp` + surgical `Edit`**: copy upstream SKILL.md, then targeted edits that swap only
  the execution layer. Far more faithful than retyping; lets you grep the exact tokens to scrub.
- **Pattern grouping**: rules-heavy System-B atomics need almost no execution swap (mostly drop the
  `自省与进化` git-commit footer + repoint the spec citation). Device skills map `mpremote`→`device_command`
  (often a clean `replace_all`). Render skills map `python G:/…render.py`→`browser_validate.diagram_render/wiring_render`.
- **Heavy-mismatch skills rewritten fresh** (deploy, flash, review): upstream esptool-venv / git-diff-CLI have no
  browser analog, so preserving them would just keep irrelevant local mechanics. Rewrote preserving the
  browser-relevant domain logic.
- **Foreground Codex review (`codex:rescue --wait`)** is the high-value gate here — it caught real leakage classes
  twice that the narrow 8-token scan missed.
- **Broadening the gate test** to encode Codex's findings (pip/uv/`python g:`/fuser/mpy-dev/`skill(`/`g:/`/etc.)
  makes the leakage permanently regression-guarded.
- **1:1 completeness audit = line-count proxy → Codex deep-diff.** A quick `browser_lines / upstream_lines` ratio per
  skill cheaply flags the egregiously-thin ones (`review` 0.18×, `flash` 0.16×); a single comprehensive Codex 1:1 pass over
  all 27 pairs then catches the same-length-but-content-swapped cases the ratio misses (it found 5 more: deploy/select-hw/
  generate/analyze/scaffold). Skills where browser ≥ upstream size are almost never gaps (content preserved + browser
  sections added). Restore **domain contracts** (taxonomies, approval gates, structured-error/decision models, result
  verdicts, field-priority tables) but NOT plugin-protocol mechanics (message payloads, host scripts) — and re-run the gate,
  which catches over-restoration (it flagged a `.flake8` host-lint rule I wrongly carried over).

## What Did NOT Work

- **Codex `--background` mode is broken in this Git-Bash/Windows env**: jobs register then evaporate (no
  persistent runtime); `result`/`cancel` report "no job found"; the companion's `taskkill /PID` gets
  MSYS-path-mangled (`/PID` → `C:/Program Files/Git/PID`). **Use foreground `--wait` only.** (`codex:rescue --wait`,
  routed to the `codex:codex-rescue` subagent. From PowerShell, `status` even shows an empty registry.)
- **Scoping "forbidden" to only the 8 tokens in the test was wrong** — device/render skills also leaked
  `pip install` / `uv tool` / `python G:/…` / `fuser` / `mpy-dev` / `Skill("…")`, none of which were in the list.
  An "all clean" 8-token scan gave false confidence. Always scan the broad local-execution set.
- **Even the "broadened" token list had a trailing-space blind spot** — `"mpremote "` (with a space) did NOT match
  `os.execvp("mpremote", …)` / `["mpremote", …]` (quote, no space), so a whole skill's host-PTY/subprocess payload
  sailed through two Codex rounds. Lesson: a substring token list is a tripwire, not proof; forbid the *spawn
  mechanism* (`os.fork`/`execvp`/`pty.openpty`/`subprocess.popen`), not just the binary-name-plus-space surface form.
- **My own "broad sweep" repeated the same mistake** — I grepped `python3 ` but every real leak was bare `python `
  (`python -c`, `python {skill_dir}/x.py`, `python test/pc/sim_main.py`), so my manual pass reported "clean" while 5
  skills still shelled out to host CPython. The Codex confirmation pass is what caught them. Lesson: you can't gate
  bare `python ` with a substring (it matches "micro**python **"); use a regex with a negative lookbehind, and never
  trust a single scan spelling — vary the surface form (`python` vs `python3`, quoted vs bare, argv-list vs CLI).
- **Naive `replace_all "upy-deploy"→"upy-deploy-browser"`** corrupts already-correct `*-browser` names
  (double-suffix). Use targeted edits for skill-name fixes, or `replace_all` only on the bare `/upy-X` slash form.
- Large multi-line `old_string` Edits failed on minor whitespace/anchor mismatches a couple times — prefer
  smaller unique anchors or read the exact block first.

## Next Steps

Migration, host-execution scrub, and the 1:1 domain audit are **done, committed, and pushed**. Remaining items are all
deferred-by-decision or future scope — nothing is blocking:

1. **Optional: one more Codex 1:1 re-verify of the 7 round-4 restorations** before relying on them in anger (they were
   verified against the upstream sections read directly + the gate, but a fresh `codex:rescue` pass over just those 7 skills
   would confirm the domain translations are faithful and no plugin-protocol mechanics leaked in).
2. **Deferred (Codex MUST-FIX #7, by decision)**: the reference `browser_skill_contract/workflow.py` firmware phase models
   only `firmware_flash_plan`, not the full resolve→download→plan→approval→execute. Happy-path smoke test, not the spec;
   expand only if the reference harness should mirror the full contract (also needs the CLI dry-run `advertised_kinds` set +
   `firmware_provider` capability).
3. **Deferred (design question, NOT a leak)**: `upy-simulate-browser` still *generates* sim code importing host
   `threading`/`rich`/`tkinter`; correctness depends on what the `simulate_run` **provider** runtime offers. Resolve when
   that provider is built.
4. **Known-acceptable residue**: `COM3` / `{port}` appear as `device_command` *arguments* (port handles the binding
   supplies), not host-shell execution — left intentionally.
5. **Out of scope this pass** (separate future effort): deepening `browser_validate` *provider implementations* (turning
   upstream helper-script logic into real network/USB/WASM/firmware providers). This pass migrated docs + reused existing
   kinds only.
6. **Dropped by user**: the "delete the failed leftover skill repos" task — user said to forget it. (For reference, candidate
   leftovers were `…/browser-micropython-skills` clone and the empty `…/blockless-project`; **never** touch the frozen
   `cursor_for_hardware` = `mpy-hardware-extension`/`mpyhw-api` stack, `MicroPython_Skills_upstream`, or this repo.)

## Verification commands (from the target repo)

```bash
python -m pytest tests -q                                              # expect 42 passed
python -m browser_skill_contract.cli catalog                          # exit 0; orchestration block present
python -m browser_skill_contract.cli dry-run-workflow --project-name blink   # status: success, firmware in chain
# broadened leak scan (must be empty):
grep -rniE "script_run|mpremote |curl |git |esptool|flake8|pylint|mpy-cross|pip install|uv tool|uv run|python g:|python -m |python --version|fuser |mpy-dev|skill\(|g:/|start-sleep|timeout /t" *-browser/SKILL.md
# host process-spawn scan (must be empty) — catches the quote-form leak the trailing-space token missed:
grep -rniE "os\.fork|execvp|Popen|pty\.openpty|termios|pexpect|\"mpremote\"" *-browser/SKILL.md
# host CPython-invocation scan (must be empty) — PCRE, excludes micropython/cpython/python_syntax/"Python 3.x" prose.
# Canonical gate is tests/test_browser_conversion_contract.py::HOST_PYTHON_INVOCATION (also catches bare `C:/` + bare `x.py`):
grep -rnP "(?<![a-z])python[0-9]? +(?:-|/|[.]|[{]|\"|'|[a-z]:/|[\w.]+/|[\w.]+[.]py)" *-browser/SKILL.md
# content-fidelity (expect 16, was 0; dropped 17→16 in round 4 when review-browser's informal "ISR"
# example was replaced by the full formal review taxonomy — cosmetic, the skill is richer, not thinner):
grep -rlE "P0|ISR|__slots__|docstring|viper|memoryview|const\(\)" *-browser/SKILL.md | wc -l
# Codex (foreground ONLY): codex:rescue --wait <review task>   (--background is broken in this env, see "What Did NOT Work")
```
