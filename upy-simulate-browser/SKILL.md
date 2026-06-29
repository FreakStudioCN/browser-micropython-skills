---
name: upy-simulate-browser
description: Use when converting upstream MicroPython skill workflows for browser-hosted simulation checks into browser-hosted primitives.
---

# upy-simulate-browser

Source skills: upy-simulate.

Use these browser primitives:
- file_operation
- browser_validate
- phase_complete

Validation kinds:
- simulate_run
- generate_quality
- python_syntax

Rules:
- Store all project files, logs, manifests, and artifacts through file_operation.
- Use device_command for board I/O and require an advertised device capability before accessing hardware.
- Use browser_validate for deterministic checks, network-backed lookup, rendering, firmware planning, and package resolution.
- Return capability_required or a partial phase result when the browser host cannot provide a required capability.
- End with phase_complete using structured status, evidence, artifacts, and next actions.
