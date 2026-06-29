---
name: upy-analyze-browser
description: Use when converting upstream MicroPython skill workflows for requirement and hardware analysis into browser-hosted primitives.
---

# upy-analyze-browser

Source skills: upy-analyze, upy-analyze-plugin.

Use these browser primitives:
- approval_request
- file_operation
- browser_validate
- phase_complete

Validation kinds:
- manifest
- manifest_phase
- package_fetch
- doc_fetch

## Inputs

- User intent text that states the desired MicroPython behavior.
- Component list with stable component ids and role/type notes.
- Optional package hints and doc links supplied by the user or prior phases.
- Optional user answers from approval_request when the requirement is ambiguous.

## Outputs

- `artifacts/analyze-manifest.json` with project name, intent, components, and package hints.
- Requirement notes or questions stored through file_operation.
- phase_complete status for the analyze phase with evidence and next action.

## Primitive Sequence

1. approval_request when the intent, component identity, or target board constraints are unclear.
2. browser_validate `doc_fetch` or `package_fetch` only when host support is advertised and external facts are required.
3. browser_validate `manifest` to normalize the request into a project manifest.
4. file_operation writes the manifest and analysis notes.
5. browser_validate `manifest_phase` checks phase readiness.
6. phase_complete returns success, partial, or failed status.

## Failure and Partial Conditions

- Return failed when the manifest lacks intent or usable components.
- Return partial with `capability_required` when doc/package lookup is needed but not advertised.
- Return partial when user approval is needed to resolve ambiguous requirements.
- Do not describe any local command as an action path; every check must use browser_validate or phase_complete.

## Rules

- Store all project files, logs, manifests, and artifacts through file_operation.
- Use browser_validate for checks, network-backed lookup, rendering, firmware planning, and package resolution.
- Return capability_required or a partial phase result when the browser host cannot provide a required capability.
- End with phase_complete using structured status, evidence, artifacts, and next actions.
