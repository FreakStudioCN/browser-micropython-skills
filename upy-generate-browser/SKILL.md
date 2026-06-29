---
name: upy-generate-browser
description: Use when converting upstream MicroPython skill workflows for firmware code generation and quality gates into browser-hosted primitives.
---

# upy-generate-browser

Source skills: upy-generate, upy-generate-plugin.

Use these browser primitives:
- approval_request
- file_operation
- browser_validate
- phase_complete

Validation kinds:
- generate_quality
- python_syntax
- package_resolve
- upypi_resolve
- mpy_compile

## Inputs

- Scaffolded files and selected hardware manifest.
- Package hints from the analyze phase.
- Optional user-approved behavior details for firmware generation.

## Outputs

- Updated firmware files under `firmware/`.
- `artifacts/generate-quality.json` with completed quality checks.
- phase_complete status for generated firmware readiness.

## Primitive Sequence

1. file_operation reads scaffolded files and selected hardware manifest.
2. approval_request asks for missing behavior details only when needed.
3. browser_validate `package_resolve` checks package needs.
4. browser_validate `upypi_resolve` resolves package metadata only when host package/network support is advertised.
5. file_operation writes generated firmware updates.
6. browser_validate `generate_quality` runs required file and semantic checks.
7. browser_validate `python_syntax` checks Python syntax.
8. browser_validate `mpy_compile` runs only when the host advertises that capability; otherwise report partial when bytecode proof is required.
9. phase_complete returns success, partial, or failed status.

## Failure and Partial Conditions

- Return failed when generated firmware lacks required files or Python syntax is invalid.
- Return partial with `capability_required: browser_validate.package_resolve` when package resolution is required but unavailable.
- Return partial with `capability_required: browser_validate.mpy_compile` when bytecode proof is required but unavailable.
- Do not name local shell tools as remedies; unsupported checks remain capability-gated.

## Rules

- Store all project files, logs, manifests, and artifacts through file_operation.
- Use browser_validate for deterministic checks, network-backed lookup, rendering, firmware planning, and package resolution.
- Return capability_required or a partial phase result when the browser host cannot provide a required capability.
- End with phase_complete using structured status, evidence, artifacts, and next actions.
