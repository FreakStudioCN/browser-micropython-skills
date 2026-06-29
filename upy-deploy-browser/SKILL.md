---
name: upy-deploy-browser
description: Use when converting upstream MicroPython skill workflows for deploy, observe, and judge device runs into browser-hosted primitives.
---

# upy-deploy-browser

Source skills: upy-deploy, upy-deploy-plugin, upy-deploy-test.

Use these browser primitives:
- approval_request
- device_command
- file_operation
- browser_validate
- phase_complete

Validation kinds:
- deploy_plan
- deploy_result_judge
- device_test_plan
- project_files

## Inputs

- Generated firmware files and selected hardware manifest.
- Optional user approval for device file replacement or clean deploy.
- Browser device adapter capability advertisement.

## Outputs

- `artifacts/deploy-plan.json` with deploy and excluded host-only files.
- Device deploy result evidence.
- phase_complete status for the deploy phase.

## Primitive Sequence

1. file_operation reads generated project files.
2. browser_validate `project_files` checks file paths before device access.
3. browser_validate `deploy_plan` selects deployable files and excludes docs, tests, tools, and mocks.
4. approval_request asks before destructive device file replacement when needed.
5. device_command `deploy` sends the approved file set only when advertised.
6. browser_validate `deploy_result_judge` checks the device result.
7. browser_validate `device_test_plan` runs only when host support is advertised and tests are requested.
8. phase_complete returns success, partial, or failed status.

## Failure and Partial Conditions

- Return failed when deploy planning or deploy result judging reports errors.
- Return partial with `capability_required: device_command.deploy` when device deploy is unavailable.
- Return partial with `capability_required: browser_validate.device_test_plan` when hardware tests are requested but unavailable.
- Real flashing, live hardware streams, and direct serial sessions remain separate capability-gated flows.

## Rules

- Store all project files, logs, manifests, and artifacts through file_operation.
- Use device_command for board I/O and require an advertised device capability before accessing hardware.
- Use browser_validate for deterministic checks, network-backed lookup, rendering, firmware planning, and package resolution.
- Return capability_required or a partial phase result when the browser host cannot provide a required capability.
- End with phase_complete using structured status, evidence, artifacts, and next actions.
