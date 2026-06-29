---
name: upy-gen-driver-browser
description: Use when converting upstream MicroPython skill workflows for driver generation from evidence sources into browser-hosted primitives.
---

# upy-gen-driver-browser

Source skills: upy-gen-driver.

Use these browser primitives:
- approval_request
- device_command
- file_operation
- browser_validate
- phase_complete

Validation kinds:
- doc_extract_pdf
- arduino_convert
- package_fetch
- generate_quality
- python_syntax

Rules:
- Store all project files, logs, manifests, and artifacts through file_operation.
- Use device_command for board I/O and require an advertised device capability before accessing hardware.
- Use browser_validate for deterministic checks, network-backed lookup, rendering, firmware planning, and package resolution.
- Return capability_required or a partial phase result when the browser host cannot provide a required capability.
- End with phase_complete using structured status, evidence, artifacts, and next actions.
