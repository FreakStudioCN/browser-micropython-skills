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

---

# ⭐ LATEST — 2026-06-29 session (aux-content re-audit + domain restorations); COMMITTED + PUSHED

> Newest close-out. Supersedes earlier sections where they conflict. **Most important reversal:** the prior "don't resurrect the deleted plugin templates" stance is REVERSED for scaffold's device-side templates — they were re-bundled into the repo. HEAD on `main` = `a7fc28a` (pushed to `FreakStudioCN/browser-micropython-skills`), preceded by `292da42`. Working tree clean.

## Goal (this session)

The user again asked to re-verify, **file-by-file vs the reference of truth** (`MicroPython_Skills_upstream`), that every `*-browser` skill is a faithful 平移. This pass deliberately checked the dimension the prior rounds under-weighted: **upstream auxiliary domain content OUTSIDE SKILL.md** — `templates/` code bodies, `knowledge/*.pitfall.json`, `references/*.md`, `boards/*.json`. Then fix any gaps.

## Current Progress (DONE — committed + pushed, working tree clean)

Full re-audit of all 27 skills (6 parallel read-only reader-subagents by cluster + my own deep reads on the 4 aux-heavy skills + a Codex foreground gate). **Verdict: 20/27 faithful; 8 items fixed** in `292da42`, plus 1 Codex must-fix in `a7fc28a`:

1. **scaffold (STRUCTURAL — highest impact).** The device-side code templates scaffold is responsible for emitting (`lib/scheduler/timer_sched.py` with the `Scheduler.add_task(callback, interval_ms, name)` API, `lib/logger` `install_rotating`, `lib/time_helper` `timed_function`/`timed_coro`, `tasks/maintenance.py`, `firmware/main_*.py.tmpl`) existed **NOWHERE** in the repo (deleted with the upstream dirs in `69fac8a`; the `generate_scaffold` validator in `validation.py` is a `print('hello')` stub) — yet `generate-browser` hard-codes their exact API. **Re-bundled 13 device-side templates** into `upy-scaffold-browser/templates/` (host `pc/` scripts EXCLUDED; the generated `README.md.tmpl` host `mpremote`/`python tools/` quick-start → Blockless-deploy prose). Wired scaffold SKILL.md Step 3 to them as **source-of-truth with a fixed-API contract table**, and grounded the scaffold↔generate contract on both ends (new generate rule "6a": call `add_task`, not `register`; `SCHEDULER_API_OR_TIMER_PORT_MISMATCH`).
2. **autofix.** Restored the ESP32 crash-signature→P-level table (`Guru Meditation`/`rst cause:4`→P1, `OSError_12`/`[FAIL]`→P2, OSError_19/110→P1, Import/Attr/Name/Syntax→P0, MemoryError→P2 — from `upy-autofix/scripts/triage.py` ERROR_PATTERNS) + the `llm_analysis` reasoning checklist (`root_cause_assessment`/`eliminated_causes`/`suspected_causes{cause,probability,test_method}`/`knowledge_gap`/`recommended_next_step` — from `diagnostic_bundle_schema.json`).
3. **analyze.** Restored the `devices[].behavior` structured enum (`role`/`event`/`active_level`/`idle_level` + the TTP223 active-low example) and the user-specified-vs-system-recommended implementation-family-lock rule.
4. **select-hw.** Restored the "firmware version is cached-only, re-check at flash time" cross-skill rule (the upstream half of flash-browser's "don't trust cached `latest_version`") and the `structured_errors` `severity`(info/warning/error/fatal) + `code` enum. Browser relabels: `script_failed`→`validate_failed`, `flash_tool esptool.py`→`serial` (Codex confirmed both correct).
5. **webserial-device-interaction.** Restored Pico USB VID:PID `2E8A:0005` + the reconnect-identity caveat.
6. **webserial-file-transfer.** Scrubbed stale host serial paths — `/dev/tty*` (initial), then `c3`/`COM3` (Codex must-fix) — consolidating the per-platform port sections into one picker-based "Device selection" block.

## What Worked

- **Audit the AUX content, not just SKILL.md.** The `-plugin`-vs-base prose diff (round 5–7 lesson) is necessary but insufficient — the biggest gap (scaffold templates) lived entirely outside SKILL.md. Inventory every skill dir's non-SKILL.md files and classify each: host-script / protocol-envelope / provider-owned-DATA (correctly dropped) vs domain knowledge (must survive).
- **`grep` the concrete artifact across the whole repo to prove "ungrounded."** `class Scheduler` / `def maintenance_tick` → NOT FOUND ANYWHERE, and `generate_scaffold` is a hello-world stub → conclusive that the scaffold↔generate API contract had no home in the repo.
- **6 parallel read-only reader-subagents by cluster** (driver-family, gen/norm-small, diagram/wiring/webserial, heavy-flagged) returning strict per-skill verdicts gave fast skeptical breadth; I personally read the 4 aux-heavy skills (generate/scaffold/analyze/autofix) to SEE the content.
- **Codex foreground gate, skill-by-skill** confirmed 7/8 clean and caught the one residual COM3 inconsistency self-review missed. A **process watcher** (poll codex node/CLI liveness, exit when gone) guarded against the known silent-evaporation failure mode — Codex ran clean this time (~8 min).
- The leak gate (`tests/test_browser_conversion_contract.py`) ONLY scans `*-browser/SKILL.md` (glob), so bundling templates under a skill dir is safe — but keep templates host-token-clean **by hand** (the gate won't catch them).

## What Did NOT Work / watch-outs

- The earlier "don't resurrect the deleted plugin templates" decision left the scaffold↔generate API contract **ungrounded**. Reversed this session. ⚠️ If a future cleanup deletes `upy-scaffold-browser/templates/` again, generate's hard-coded `add_task`/`install_rotating` references break **silently** (PC tests pass; the device crashes per the `esp32_timer_scheduler_api` pitfall). Treat `upy-scaffold-browser/templates/` as load-bearing.
- `COM3`-as-`device_command`-arg was previously deemed "acceptable residue" — but in a file that ALSO asserts "no host port paths" it's an internal contradiction (Codex flagged it for file-transfer). Acceptable where no picker-only claim is made (device-interaction), not where it is.

## Next Steps (optional / deferred — nothing blocking)

1. **Build the real `scaffold_generate` provider** so it emits the now-bundled `upy-scaffold-browser/templates/` verbatim (only `${...}` substitution). The reference validator in `validation.py` is still a hello-world stub; the fixed-API contract table in scaffold SKILL.md Step 3 is the spec.
2. **Provider-owned upstream DATA, confirm ownership (intentionally NOT bundled):** `upy-generate-plugin/knowledge/micropython_official_library_index.json` (7359 lines) + `cloud_service_catalog.json` (242) → `package_resolve`/`upypi_resolve` + cloud providers; `upy-analyze-plugin/boards/*.json` (board-facts source-of-truth) → consumed by select-hw, not analyze.
3. **Optional:** update the older sections' "all domain knowledge aligned" framing (now refined — aux content was the gap).

## Verification (from the target repo)

```bash
python -m pytest tests -q -p no:cacheprovider                         # 42 passed
python -m browser_skill_contract.cli dry-run-workflow --project-name blink   # status: success
# 3 leak scans on *-browser/SKILL.md must be empty (exact greps in the older close-out section below):
#   host-shell tokens / host-spawn (os.fork|execvp|Popen|pty.openpty|pexpect|"mpremote") / host-python PCRE
grep -rniE "esptool|mpremote|/dev/tty|com[0-9]| g:/" upy-scaffold-browser/templates/   # bundled templates clean (empty)
```

---

# 2026-06-29 session (prior close-out): firmware chain + docs cleanup + simulate → MicroPython-WASM

> This section supersedes the round-1–7 "Next Steps" where they conflict. It closes out the remaining open items from the prior session. **Committed + pushed to `main`:** `11cf54c` (the close-out) and `801c69b` (Codex round-2 MicroPython fixes). Working tree clean.

## What this session closed

1. **Firmware chain in the reference smoke harness (was Codex MUST-FIX #7 / deferred).** `run_main_browser_workflow` (`workflow.py`) now exercises the full firmware contract chain the `upy-flash-mpy-firmware-browser` skill declares: `firmware_page_resolve → firmware_download → firmware_flash_plan → firmware_flash_execute` (was only `firmware_flash_plan`). The handlers for all 5 firmware kinds already existed in `validation.py`; only the workflow call-chain + the CLI dry-run `advertised_kinds` set (`cli.py`) were stubbed — both now wired. A human `approval_request` (esp32_flash_confirm) can't run in a non-interactive smoke run, so the happy path is download_and_flash with a comment that production must still gate flash_execute on user confirmation. Tests updated: `_validator()` advertises the 3 new kinds; `..._returns_partial_without_firmware_provider` now expects `browser_validate.firmware_page_resolve` (the new first firmware step).

2. **Docs hygiene (was Next Step #1).** Deleted 3 top-level guide `.md`s that were **byte-identical duplicates** of the `docs/reference/` copies (every skill cites the `docs/reference/` path; nothing cited top-level), plus the unreferenced `upy-select-hw-plugin-generic-modification-plan.md`. Updated `README.md` (dropped the false "upstream skill dirs retained" row + line-5 framing; firmware-chain line). `pytest` still 42 after deletion (the hardcoded-path tests reference only `adapters/`+`docs/`, not the deleted files).

3. **`upy-analyze-browser` resource gap (was Next Step #2) — confirmed already closed.** Zero dangling `templates/*.json` refs; field shapes point to in-file models + `contracts/`. No browser skill bundles example-message files — all 27 use the same in-file+`contracts/` pattern, so analyze is consistent. Nothing to fix.

4. **`upy-simulate-browser` host imports (was the big deferred design question) — REWRITTEN for the real runtime.** ⚠️ **KEY FINDING that corrected a wrong assumption:** the `simulate_run` provider's in-browser runtime is **MicroPython compiled to WASM** — the same runtime ViperIDE uses (`@micropython/micropython-webassembly-pyscript@^1.24.1`, confirmed in `viperide-fork/package.json`; ViperIDE also bundles `@xterm/xterm`, `@pybricks/mpy-cross-v6`, `@astral-sh/ruff-wasm-web`). It is **NOT Pyodide/CPython**. (The product is a webapp — everything runs in the browser, there is no host.) Consequence: the generated sim code was changed to target MicroPython-WASM — `thread` mode → cooperative `asyncio` (no OS threads), timer `SimScheduler` → `await asyncio.sleep` (not blocking `time.sleep`), **removed `tkinter` entirely** (no host GUI), and **removed `rich` entirely** (CPython-only, absent in MicroPython). Visualization is now plain `print()`/ANSI text rendered by the provider's in-browser terminal (xterm), or structured per-tick JSON for a canvas view; `--mode cli|gui` → `--mode terminal|canvas`. All domain sections (project classification, mock patterns, data generators, coverage dimensions, NL→mock mapping, PASS/WEAK_PASS/FAIL) left intact.

## Verification (this session)

- `python -m pytest tests -q` → **42 passed**; `cli dry-run-workflow` → `success` and now exercises all 4 firmware kinds (`firmware-flash-plan.json` artifact still produced).
- All 3 leak scans (host-shell / host-spawn / host-python) → **empty**; fidelity count → **16** (unchanged).
- **Codex review (round 1, full diff):** domain retention CLEAN, firmware chain CLEAN, docs deletions CLEAN. Raised 2 MUST-FIX on the simulate file — but both assumed Pyodide (rich `Live` defaults; `asyncio.run()` vs already-running JS loop). Both **dissolved** by the MicroPython-WASM correction (rich removed; `asyncio.run` is idiomatic for MicroPython-WASM and the provider owns entry scheduling).
- **Codex review (round 2):** focused re-verify of the simulate file for MicroPython-WASM correctness → items "no CPython-only assumptions", "asyncio entry sound", "domain intact" all **CLEAN**; 2 MUST-FIX on the example code (`gen_bmp280` used `math.*` without `import math`; guidance used `os.path.join`, which MicroPython lacks) — both fixed in `801c69b` (plain string path; added `import math`). `pytest` 42 passed, leak scans empty after the fix.

## What worked (this session)

- **Trace each open item to ground truth before touching code.** The firmware-chain handlers + `firmware_provider` capability already existed in `validation.py`/`cli.py` — only the workflow call-chain + the CLI `advertised_kinds` were stubbed; and `upy-analyze-browser` was already consistent (zero dangling refs). Reading first meant I wired what was missing instead of inventing fixes that weren't needed.
- **Verify the runtime against the dependency, not intuition.** Reading `viperide-fork/package.json` (→ `@micropython/micropython-webassembly-pyscript`) is what proved the sim runtime is MicroPython-WASM and overturned the Pyodide assumption — a `grep`/`package.json` check beat a plausible-sounding guess.
- **Two-pass Codex gate.** Round 1 over the full diff (confirmed domain/firmware/docs CLEAN); round 2 focused on MicroPython validity of the simulate examples (caught the missing `import math` in `gen_bmp280` + the `os.path.join` that MicroPython lacks). Self-review + the leak scans missed both.
- **Surgical runtime-only edits.** Swapping only scheduling / visualization / library wording and leaving every domain section (mock patterns, scenarios, coverage dims, NL→mock mapping) untouched is why Codex confirmed domain retention CLEAN on both passes.

## What Did NOT Work / lesson

- **Assuming "browser WASM == Pyodide (CPython)".** First instinct was Pyodide, so the first simulate rewrite KEPT `rich` (reframed as xterm-rendered). Wrong: the stack reuses ViperIDE's runtime = **MicroPython-WASM**, where `rich`/CPython-only libs don't exist. First-principles check of `viperide-fork/package.json` (the dependency, not the assumption) is what caught it. Lesson: verify the actual runtime dependency before designing generated-code guidance against it.

## Still open / deferred (unchanged from before, NOT blocking)

- `simulate_run` **provider implementation** is still out of scope (this pass only fixed the *generated-code guidance* to target the right runtime). The provider's exact entrypoint convention (how it invokes `async main()`) is documented as "provider schedules the entry"; confirm when the provider is built.
- `browser_skill_contract/workflow.py` is a happy-path smoke harness; it does not model the approval gate or firmware_action variants (download_only / already_flashed / …) — by design for a non-interactive dry run.

---

# 2026-06-29 session (rounds 5–7): full 平移 audit + plugin-sibling restoration + repo cleanup

> This section supersedes the round 1–4 history below where they conflict. **Most important structural change: the repo no longer contains the old upstream/`-plugin`/`-test` source dirs** — they were deleted (commit `69fac8a`). The round 1–4 text below still refers to them as present; that history is preserved for context only.

## Goal (this session)

The user asked to re-verify, **one skill at a time, against the reference of truth** (`MicroPython_Skills_upstream`), that each `*-browser` skill is a faithful **平移 (1:1 lateral port)** — identical design / detail / domain knowledge, with ONLY the execution layer swapped to the 5 Blockless primitives — and to quantify the misalignment. Then (their follow-up) to **delete the redundant old source skills** from this repo.

## Current Progress (DONE, committed + pushed, working tree clean)

Three commits on `main` this session:
- **`8616073`** — restored `upy-flash-mpy-firmware-browser` (it was a fresh rewrite that had GUTTED real firmware/ESP32 domain knowledge) + fixed `review-browser` (high/critical→`blocking/suggestion/nitpick` severity inconsistency; restored standalone topic-search + `--style-only`).
- **`da17142`** — restored plugin-sibling domain drops in `upy-select-hw-browser` (I2S allocation rule, `flash_tool`/`board_unavailable` enums, `pin_review`/`user_pin_constraints` models, UART-reuse rule, cold-driver rule, pin_options remap; fixed stale single-`i2s` type row), `upy-generate-browser` (Scheduler `timer_id` port rule, boot fatal-guard + `error_cb`, 2 `check_generated_semantics` anti-patterns, async anti-circumvention rule, `cold_driver_required` gating, doc_evidence specific-`machine.*` precision, ASCII-comment rule, `_thread` mode), and `upy-scaffold-browser` (`docs/.gitkeep` + no-fake-tools rule).
- **`69fac8a`** — **deleted 35 redundant old dirs (326 files)**: all non-`-browser` skill copies + `-plugin`/`-test` variants + `shared-plugin-scripts` + `upy-project-gen-toolchain-spec`. Fixed 2 browser skills that referenced now-deleted resources (`upy-analyze-browser` templates/mock-messages/`references/v0-protocol.md` → its own in-file field models + `contracts/`; `upy-pkg-guide-browser` `scripts/search_awesome.py` description → attributed to the `browser_validate (awesome_micropython_search)` provider).

**Final repo surface:** 27 `*-browser/` skills + `browser_skill_contract/` + `contracts/` + `adapters/` + `docs/` + `tests/`. Every step gated: `python -m pytest tests -q` → **42 passed**; the 3 host-execution leak scans → **empty**.

**Misalignment verdict (the user's original question):** of 27 skills, all domain knowledge is now aligned. The lossy ones were `flash` (worst — gutted, ~45/100 before fix), then `select-hw` (88) and `generate` (93); `analyze` (94) and `scaffold` (92) were already clean. All restored to faithful 平移.

## What Worked

- **Diff each browser skill against its `-plugin` sibling, NOT just the base skill.** This is the key lesson. Each `*-browser` skill MERGES two upstream files: `upy-X` (base) + `upy-X-plugin` (content-rich). The original audits compared only against the base skill → a browser skill looked "richer/aligned" while it had actually condensed away domain knowledge that lived in the `-plugin`. Re-diffing vs the `-plugin` is what exposed the select-hw/generate drops.
- **Why the drops happen:** in the `-plugin`, domain rules are INTERLEAVED with protocol-envelope JSON (~30–50% of each `-plugin` file is repeated `start_phase`/`state`/`phase_complete`/`approval_request` envelopes). When the migration stripped the envelopes, it dropped domain rules tangled up with them. The protocol boilerplate is correctly abstracted into `contracts/*.schema.json` (every browser skill cites it) — do NOT re-inline it; only restore the DOMAIN enums/rules, which belong in the skill.
- **Parallel reader-subagents** (one per skill-cluster / one per pair) returning a strict structured verdict (SCORE / VERDICT / DROPPED_DOMAIN / …) gave fast, skeptical breadth; **Codex (`codex:rescue`/`codex:codex-rescue`, foreground) as an independent gate** confirmed flash's 9/9 domain drops and caught review gaps the readers under-weighted.
- **Token-presence provenance scan** (`grep -c` a distinctive token in browser vs base vs plugin) cheaply proves "nothing INVENTED" — but it does NOT prove "nothing DROPPED"; only a section-by-section content diff does. Don't stop at the grep.
- **Delete-then-`pytest` as the safety net:** listed the keep/delete sets, deleted, then ran pytest — it immediately caught that `adapters/` had been wrongly deleted (restored via `git checkout HEAD -- adapters`).
- **Restoring with browser-appropriate values** to satisfy the leak gate: e.g. `flash_tool` ESP value = `serial` (not the host flasher name), renamed `esptool_failed`→`flash_execute_failed`.

## What Did NOT Work

- **The first full audit's "26/27 aligned / browser is richer than upstream" was over-optimistic** — because it compared vs the BASE skill only. "Richer than upstream" is NOT automatically good for a 1:1 port; it's only fine if the extra content traces to an upstream `-plugin` sibling (it did, via merge), and it MASKED the fact that other plugin domain content was dropped. Always diff vs the `-plugin`.
- **Almost deleted `adapters/`** with the old source dirs — `adapters/` is browser-contract infrastructure (device-binding / validation / artifact-store docs) required by `tests/test_browser_conversion_contract.py::test_contract_files_exist`, NOT an old skill copy. Keep-set for deletion = `*-browser`, `browser_skill_contract`, `contracts`, `adapters`, `docs`, `tests`.
- **A naive "does any .py read an old dir" grep is not sufficient** to clear a deletion — `test_browser_conversion_contract.py` references `adapters/*` and `docs/*` by hardcoded path lists, and the catalog uses a string `source→browser` map (not a fs scan). Run pytest after deleting; don't trust a single grep.

## Next Steps (all optional / deferred — nothing blocking)

1. **Docs hygiene:** update the repo `README.md` (and this HANDOFF's older sections) to describe the new clean structure — they predate the deletion and still imply the old source dirs are present.
2. **`upy-analyze-browser` resource gap (acknowledged, repointed, not fully closed):** its SKILL.md tells the LLM to follow envelope/checkpoint/structured_error/artifact shapes; those shapes are defined in its own prose + `contracts/` now (the broken `templates/*.json` refs were repointed), but there are no longer concrete example-message files bundled. If worked examples are wanted, add real ones under the browser dir or expand `contracts/` — don't resurrect the deleted plugin templates.
3. **Deferred (still true):** `upy-simulate-browser` still *generates* sim code importing host `threading`/`rich`/`tkinter` — resolve when the `simulate_run` provider runtime is decided. Reference `browser_skill_contract/workflow.py` firmware phase models only `firmware_flash_plan`, not the full resolve→download→plan→approval→execute chain (round-4 Codex MUST-FIX #7).
4. **Source of truth for re-audits:** `MicroPython_Skills_upstream/` (has remote `FreakStudioCN/MicroPython_Skills`); each browser skill = base `upy-X` ⊕ `upy-X-plugin`. The `webserial-*-browser` map to `mpremote-*`; `upy-flash-mpy-firmware-browser` maps to `upy-flash-mpy-firmware-plugin`.

---

# ⬇️ HISTORY (rounds 1–4, 2026-06-28) — preserved for context; repo structure described below is now stale (old dirs deleted)

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
