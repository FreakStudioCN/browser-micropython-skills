---
name: upy-select-hw-browser
description: Use when converting upstream MicroPython skill workflows for board selection and pin planning into browser-hosted primitives.
---

# upy-select-hw-browser

Source skills: upy-select-hw, upy-select-hw-plugin.

Use these browser primitives:
- approval_request
- device_command
- file_operation
- browser_validate
- phase_complete

Validation kinds:
- select_hw_manifest
- manifest_phase

## Inputs

- Analyze manifest from `artifacts/analyze-manifest.json`.
- Optional board preference, available connector notes, and user constraints.
- Optional browser device probe result from device_command.

## Outputs

- `artifacts/select-hw-manifest.json` with selected board and pin plan.
- Pin assignment notes stored through file_operation.
- phase_complete status for board and pin selection.

## Primitive Sequence

1. file_operation reads the analyze manifest.
2. device_command `probe` runs only when host device access is advertised and user consent has already opened a port.
3. approval_request asks the user to choose or revise a board when automatic selection is incomplete.
4. browser_validate `select_hw_manifest` checks board and pin assignments against the manifest.
5. browser_validate `manifest_phase` checks phase readiness.
6. file_operation writes the selected hardware manifest and notes.
7. phase_complete returns success, partial, or failed status.

## Failure and Partial Conditions

- Return failed when selected pins reference unknown components or required board fields are missing.
- Return partial with `capability_required: device_command.probe` when board probing is required but unavailable.
- Return partial when the user must choose among valid board or pin options.
- Do not route board work through local host commands; device access is device_command only.

## Rules

- Store all project files, logs, manifests, and artifacts through file_operation.
- Use device_command for board I/O and require an advertised device capability before accessing hardware.
- Use browser_validate for deterministic checks, rendering, firmware planning, and package resolution.
- Return capability_required or a partial phase result when the browser host cannot provide a required capability.
- End with phase_complete using structured status, evidence, artifacts, and next actions.
