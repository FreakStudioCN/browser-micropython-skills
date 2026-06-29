---
name: webserial-live-session-browser
description: Use when converting upstream MicroPython skill workflows for serial output observation without interrupting the running program into browser-hosted primitives.
---

# webserial-live-session-browser

Source skills: mpremote-live-session.

Use these browser primitives:
- approval_request
- device_command
- file_operation
- phase_complete

Validation kinds:
- device_test_plan

Rules:
- Store all project files, logs, manifests, and artifacts through file_operation.
- Use device_command for board I/O and require an advertised device capability before accessing hardware.
- Use browser_validate for deterministic checks, network-backed lookup, rendering, firmware planning, and package resolution.
- Return capability_required or a partial phase result when the browser host cannot provide a required capability.
- End with phase_complete using structured status, evidence, artifacts, and next actions.
