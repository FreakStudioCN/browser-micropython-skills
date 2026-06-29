# Blockless Device Binding

`device_command` is the Blockless Web Builder boundary for USB board work.

Blockless owns the user gesture, WebSerial/WebUSB permission flow, project state, and deployment UI. ViperIDE code may be used as implementation reference for raw REPL and file transfer behavior, but it is not a runtime target for this skill repository.

Required actions:

| Action | Blockless responsibility |
| --- | --- |
| `connect_request` | Trigger the browser USB permission flow from a user gesture. |
| `scan` | Return the current authorized device and USB metadata when available. |
| `probe` | Read board identity using browser serial execution. |
| `exec` | Execute a short command and return stdout, stderr, and status. |
| `cp` / `deploy` | Write project files to explicit device paths. |
| `cp_from` | Read explicit device paths into Blockless artifacts. |
| `ls` / `mkdir` / `rm` / `statvfs` | Map file-system operations through browser device helpers. |
| `soft_reset` | Reset the interpreter without assuming physical reset support. |
| `hard_reset` | Use browser-exposed signal support when available; otherwise ask the user to press reset. |
| `stream` | Observe serial output without interrupting the running application. |
| `mip_install` | Install packages through the connected device when Blockless has network/device support. |

Path handling must be explicit and escaped. Deployment must exclude mocks, local tools, tests, docs, and host-only artifacts unless the skill asks for them by path.
