# Blockless Browser Capability Matrix

This repo translates upstream MicroPython skill behavior into Blockless browser primitives.

| Capability family | Browser primitive | Required Blockless support |
| --- | --- | --- |
| User decisions | `approval_request` | Blockless UI surface |
| Project files and artifacts | `file_operation` | Blockless project store |
| Board access | `device_command` | Secure context plus Blockless WebSerial/WebUSB binding |
| Static checks and network fetches | `browser_validate` | Browser, WASM, or Blockless-owned validation provider |
| Phase output | `phase_complete` | Structured workflow envelope |

Device flashing, hard reset, compiled bytecode checks, PDF extraction, package resolution, and review indexing are Blockless runtime capabilities. A browser skill returns `capability_required` only when the current Blockless session is missing required state such as login, USB permission, a connected device, or a loaded provider.
