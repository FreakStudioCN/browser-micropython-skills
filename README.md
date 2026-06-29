# Blockless MicroPython Browser Skills

Blockless Web Builder skill repository for browser-native MicroPython hardware workflows.

This repository starts from the upstream `FreakStudioCN/MicroPython_Skills` skill tree, keeps those skills as reference material, and adds Blockless-first browser skills that run through the Blockless web product without leaking local shell assumptions.

## Design Rule

Blockless browser skills may only use these primitives:

- `approval_request`
- `file_operation`
- `device_command`
- `browser_validate`
- `phase_complete`

Do not add `script_run` back. Do not make browser skill steps depend on local `mpremote`, `curl`, `git`, `esptool`, `flake8`, `pylint`, or `mpy-cross` commands. Those capabilities must be implemented through Blockless browser bindings. `capability_required` means the current Blockless runtime is missing state such as login, USB permission, a connected device, or a loaded provider.

## Repository Layout

| Path | Purpose |
| --- | --- |
| `browser_skill_manifest.json` | Source of truth for upstream skill to Blockless browser skill mapping. |
| `contracts/` | JSON schemas and capability matrix. |
| `adapters/` | Blockless runtime binding docs for device, validation, and artifact storage. |
| `browser_skill_contract/` | Reference Python runtime for CI and contract tests. |
| `*-browser/SKILL.md` | Blockless browser skill definitions. |
| upstream skill dirs | Original upstream skills retained as conversion references. |
| `tests/` | Contract, runtime, validation, CLI, and workflow tests. |

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
- Browser validation providers for MVP flow: project files, Python syntax, scaffold generation, scaffold contract, deploy plan, deploy result judge.
- Fake device binding for contract tests and dry runs.
- Reference analyze -> select-hw -> scaffold -> generate -> deploy workflow.

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
