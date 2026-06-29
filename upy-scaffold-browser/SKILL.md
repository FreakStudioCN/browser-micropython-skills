---
name: upy-scaffold-browser
description: Use when converting upstream MicroPython skill workflows for project scaffold generation into browser-hosted primitives.
---

# upy-scaffold-browser

Source skills: upy-scaffold, upy-scaffold-plugin.

Use these browser primitives:
- approval_request
- file_operation
- browser_validate
- phase_complete

Validation kinds:
- scaffold_generate
- scaffold_contract
- project_files
- python_syntax

## Inputs

- Selected hardware manifest from `artifacts/select-hw-manifest.json`.
- Project name, scheduler preference, and optional extra host-only files.
- Optional scaffold settings approved by the user.

## Outputs

- Firmware files under `firmware/`.
- Optional support files under `lib/`.
- Scaffold artifacts and phase_complete status for scaffold readiness.

## Primitive Sequence

1. file_operation reads the selected hardware manifest.
2. approval_request asks for scaffold mode only when the manifest does not make it clear.
3. browser_validate `scaffold_generate` creates the browser-safe file set.
4. file_operation writes generated files and artifacts.
5. browser_validate `scaffold_contract` checks required files.
6. browser_validate `project_files` checks project-relative paths.
7. browser_validate `python_syntax` checks Python syntax.
8. phase_complete returns success, partial, or failed status.

## Failure and Partial Conditions

- Return failed when required firmware files are missing or Python syntax is invalid.
- Return partial when scaffold settings need user approval before files are written.
- Return partial with `capability_required` when a needed validation kind is not advertised.
- Do not emit local command steps; generation and checks are browser_validate providers.

## Rules

- Store all project files, logs, manifests, and artifacts through file_operation.
- Use browser_validate for deterministic checks, rendering, firmware planning, and package resolution.
- Return capability_required or a partial phase result when the browser host cannot provide a required capability.
- End with phase_complete using structured status, evidence, artifacts, and next actions.
