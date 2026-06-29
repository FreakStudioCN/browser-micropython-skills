---
name: upy-gen-readme-browser
description: Use when converting upstream MicroPython skill workflows for readme generation into browser-hosted primitives.
---

# upy-gen-readme-browser

Source skills: upy-gen-readme.

Use these browser primitives:
- file_operation
- browser_validate
- phase_complete

Validation kinds:
- project_files

Rules:
- Store all project files, logs, manifests, and artifacts through file_operation.
- Use device_command for board I/O and require an advertised device capability before accessing hardware.
- Use browser_validate for deterministic checks, network-backed lookup, rendering, firmware planning, and package resolution.
- Return capability_required or a partial phase result when the browser host cannot provide a required capability.
- End with phase_complete using structured status, evidence, artifacts, and next actions.
