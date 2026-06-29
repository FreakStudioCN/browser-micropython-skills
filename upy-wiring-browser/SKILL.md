---
name: upy-wiring-browser
description: Use when converting upstream MicroPython skill workflows for wiring plans and rendered wiring artifacts into browser-hosted primitives.
---

# upy-wiring-browser

Source skills: upy-wiring.

Use these browser primitives:
- approval_request
- file_operation
- browser_validate
- phase_complete

Validation kinds:
- wiring
- wiring_render
- diagram_mermaid

Rules:
- Store all project files, logs, manifests, and artifacts through file_operation.
- Use device_command for board I/O and require an advertised device capability before accessing hardware.
- Use browser_validate for deterministic checks, network-backed lookup, rendering, firmware planning, and package resolution.
- Return capability_required or a partial phase result when the browser host cannot provide a required capability.
- End with phase_complete using structured status, evidence, artifacts, and next actions.
