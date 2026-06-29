# Blockless MicroPython Browser Skills

Blockless Web Builder skill repository for browser-native MicroPython hardware workflows. Blockless Web Builder is the only target runtime. ViperIDE is only an implementation reference for browser serial and device techniques.

This repository is derived from the upstream `FreakStudioCN/MicroPython_Skills` skill tree (kept as a separate reference-of-truth repo, not vendored here) and provides Blockless-first browser skills that run through the Blockless web product without leaking local shell assumptions. The repo holds the 27 `*-browser/SKILL.md` skills plus contract infrastructure; the original upstream/plugin source skills are not kept here.

## Design Rule

Blockless browser skills may only use these primitives:

- `approval_request`
- `file_operation`
- `device_command`
- `browser_validate`
- `phase_complete`

Do not add `script_run` back. Do not make browser skill steps depend on local `mpremote`, `curl`, `git`, `esptool`, `flake8`, `pylint`, or `mpy-cross` commands. Those capabilities must be implemented through Blockless browser bindings. `capability_required` means the current Blockless runtime is missing state such as login, USB permission, a connected device, or a loaded provider.

## Skill Content & Structure

Each `*-browser/SKILL.md` carries the **full domain content** of its upstream source (the P0–P2 rule
checklists, section templates, optimization tables, and code templates), with only the *execution layer*
swapped to Blockless primitives. They are not thin stubs — a browser skill is contract sections + the upstream
rules, expressed through Blockless bindings.

The 27 skills mirror the upstream **two-spine, three-tier** structure (project pipeline / driver normalization,
over orchestrator / phase / atomic / tool). The relationship is encoded as data in the manifest
(`tier`/`spine`/`phase`/`orchestrates`/`calls`), surfaced by `cli catalog` under `orchestration`, and
documented in `docs/skill-orchestration-map.md`.

**Boundary:** a skill's domain rewriting/generation is done by the LLM applying its embedded rules;
`browser_validate` only performs the objective, decidable subset (parse / structure / provider-backed fetch /
render). A validation kind never replaces the rule checklist. Each skill states this in its
"domain … vs browser_validate" section.

## Repository Layout

| Path | Purpose |
| --- | --- |
| `browser_skill_manifest.json` | Source of truth for upstream skill to Blockless browser skill mapping. |
| `contracts/` | JSON schemas and capability matrix. |
| `adapters/` | Blockless runtime binding docs for device, validation, and artifact storage. |
| `browser_skill_contract/` | Reference Python runtime for CI and contract tests. |
| `*-browser/SKILL.md` | Blockless browser skill definitions (27 skills). |
| `tests/` | Contract, runtime, validation, CLI, and workflow tests. |
| `docs/plugin-capability-crosswalk.md` | Upstream/plugin capability to Blockless primitive mapping. |
| `docs/skill-orchestration-map.md` | Two-spine / three-tier skill graph (orchestrators, phases, edges). |
| `docs/reference/` | Bundled GraftSense spec + performance/memory guides cited by the normalization/optimization skills. |

## Runtime Helpers

List the browser catalog:

```bash
python -m browser_skill_contract.cli catalog
```

Run the reference Blockless browser workflow dry run:

```bash
python -m browser_skill_contract.cli dry-run-workflow --project-name blink
```

Run tests:

```bash
python -m pytest tests -q
```

## Implemented Contract Surface

The current implementation includes:

- Manifest loading and source/browser skill indexing.
- Primitive envelope validation.
- Device command action validation.
- Browser validation kind validation.
- Capability negotiation helpers.
- In-memory project artifact store.
- Default browser validation router registration for all 33 declared validation kinds. Deterministic providers run in the reference runtime; Blockless runtime providers return structured partial results until provider state is supplied.
- Fake device binding for contract tests and dry runs.
- Reference analyze -> select-hw -> firmware (page resolve -> download -> flash plan -> flash execute) -> scaffold -> generate -> deploy workflow.

## Blockless Runtime States

Upstream local commands are replaced by Blockless browser bindings:

| Upstream capability | Blockless browser handling |
| --- | --- |
| serial port enumeration | User-authorized WebSerial/WebUSB device flow. |
| named COM/tty connection | Blockless USB picker from a user gesture. |
| hard reset | Browser-exposed serial signals or Blockless reset prompt. |
| local PTY live REPL | Blockless serial stream and command execution. |
| firmware flashing tools | Blockless browser flasher flow. |
| UF2 mount scan/copy | Blockless file picker or browser file-system flow. |
| bytecode compilation | WASM or Blockless validation provider. |
| package install/resolve | Blockless package registry and device/network flow. |
| review context | `browser_validate(review_context/review_verify)`. |
| network document fetch | `browser_validate(doc_fetch/package_fetch)`. |
| lint/test commands | `browser_validate(...)`. |

`capability_required` is reserved for current Blockless runtime state gaps: missing login, missing provider, unavailable browser API, missing USB permission, or no connected board.

## Blockless Consumption

See `docs/blockless-consuming-browser-skill-contract.md`.
