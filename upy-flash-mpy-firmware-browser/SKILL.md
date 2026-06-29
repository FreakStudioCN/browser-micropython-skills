---
name: upy-flash-mpy-firmware-browser
description: Use when converting upstream MicroPython skill workflows for firmware readiness, download, and flashing plans into browser-hosted primitives.
---

# upy-flash-mpy-firmware-browser

Source skills: upy-flash-mpy-firmware-plugin.

Use these browser primitives:
- approval_request
- file_operation
- browser_validate
- phase_complete

Validation kinds:
- firmware_page_resolve
- firmware_download
- firmware_flash_plan
- firmware_flash_execute
- uf2_manual_confirm

Rules:
- Store all project files, logs, manifests, and artifacts through file_operation.
- Use device_command for board I/O and require an advertised device capability before accessing hardware.
- Use browser_validate for deterministic checks, network-backed lookup, rendering, firmware planning, and package resolution.
- Return capability_required or a partial phase result when the browser host cannot provide a required capability.
- End with phase_complete using structured status, evidence, artifacts, and next actions.
