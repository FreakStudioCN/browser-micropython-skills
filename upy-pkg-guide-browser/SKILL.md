---
name: upy-pkg-guide-browser
description: Use when converting upstream MicroPython skill workflows for package discovery guidance into browser-hosted primitives.
---

# upy-pkg-guide-browser

Source skills: upy-pkg-guide.

Use these browser primitives:
- browser_validate
- file_operation
- phase_complete

Validation kinds:
- package_fetch
- package_resolve
- awesome_micropython_search
- doc_fetch

Rules:
- Store all project files, logs, manifests, and artifacts through file_operation.
- Use device_command for board I/O and require an advertised device capability before accessing hardware.
- Use browser_validate for deterministic checks, network-backed lookup, rendering, firmware planning, and package resolution.
- Return capability_required or a partial phase result when the browser host cannot provide a required capability.
- End with phase_complete using structured status, evidence, artifacts, and next actions.
