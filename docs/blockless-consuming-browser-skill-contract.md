# Blockless Consumption of Browser Skill Contracts

This document defines how Blockless consumes the browser MicroPython skill contract without reintroducing local execution assumptions into the skill layer.

## Inputs

Blockless reads `browser_skill_manifest.json` as the source of truth. Each entry declares:

| Field | Meaning |
| --- | --- |
| `source_skills` | Upstream reference skill directories covered by the browser skill. |
| `browser_skill` | Blockless browser skill directory exposed to the workflow. |
| `primitives` | Allowed Blockless primitive calls for that skill. |
| `browser_validate_kinds` | Validation jobs Blockless must route to browser, WASM, or Blockless-owned providers. |

Blockless also loads:

- `contracts/browser_tools.schema.json`
- `contracts/device_command.schema.json`
- `contracts/browser_validate.schema.json`
- `contracts/capability_matrix.md`

## Blockless Responsibilities

Blockless is the runtime for these skills.

It should:

1. Serve the browser skill catalog from `browser_skill_manifest.json`.
2. Advertise current runtime state to the workflow.
3. Validate every tool envelope against the JSON schemas.
4. Route primitive calls to Blockless project storage, device, validation, UI, or artifact bindings.
5. Return structured `success`, `partial`, `failed`, or `capability_required` results.
6. Persist artifacts only through the Blockless project artifact interface.

It must not:

1. Let a browser skill invoke arbitrary local commands.
2. Convert browser skill text back into host-specific command strings.
3. Assume serial port names, local filesystem paths, package managers, or firmware tools exist.
4. Hide missing runtime state by doing unexpected privileged work.

## Runtime State

Before a phase starts, Blockless should provide a runtime state object similar to:

```json
{
  "auth": {"signed_in": true},
  "browser": {"webserial": true, "webusb": true},
  "device_command": ["connect_request", "scan", "probe", "exec", "cp", "deploy", "stream"],
  "browser_validate": ["python_syntax", "project_files", "deploy_plan"],
  "artifact_store": ["read", "write", "list", "delete", "snapshot"],
  "providers_loaded": ["python_syntax", "project_files"]
}
```

If required state is missing, Blockless returns:

```json
{
  "status": "partial",
  "capability_required": "device_command.connect_request",
  "next_action": "connect_device"
}
```

## Primitive Routing

| Primitive | Blockless routing |
| --- | --- |
| `approval_request` | Render Blockless UI and wait for an explicit user response. |
| `file_operation` | Read/write/list/delete/snapshot project-relative files in the Blockless project store. |
| `device_command` | Run through Blockless browser device binding. |
| `browser_validate` | Run a declared Blockless validation provider. |
| `phase_complete` | Persist the final structured phase envelope and expose it to the builder UI. |

## Device Commands

Blockless owns board transport state because the browser has the active USB permission. Device actions should go through the Blockless device binding and persist returned evidence.

Required response shape:

```json
{
  "status": "success",
  "action": "probe",
  "stdout": "...",
  "stderr": "",
  "artifacts": []
}
```

For missing runtime state:

```json
{
  "status": "partial",
  "action": "deploy",
  "capability_required": "device_command.connect_request",
  "next_action": "connect_device"
}
```

## Validation Jobs

`browser_validate` is the Blockless replacement for upstream scripts, static checks, document fetches, package lookup, firmware planning, rendering, and review verification.

A validation provider must declare the kinds it supports. Blockless rejects undeclared kinds and returns `capability_required` for declared but currently unavailable providers.

## Runtime Helper

The reference runtime in `browser_skill_contract/` gives CI a small executable contract surface:

```bash
python -m browser_skill_contract.cli catalog
python -m browser_skill_contract.cli dry-run-workflow --project-name blink
```

Use `catalog` in CI to verify that the manifest can be loaded and indexed. Use `dry-run-workflow` as a smoke test for the reference Blockless workflow without requiring real hardware.

## Migration Rule

When adding a new browser skill or validation kind, update these files in the same change:

1. `browser_skill_manifest.json`
2. The relevant `contracts/*.schema.json`
3. The browser skill `SKILL.md`
4. `tests/test_browser_conversion_contract.py` if the contract shape changes

The test suite is the guardrail that proves the upstream skill surface is still mapped into Blockless browser skills.
