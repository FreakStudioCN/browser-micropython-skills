---
name: webserial-device-interaction-browser
description: General MicroPython device interaction over the Blockless device binding (device_command) inside Blockless Web Builder — connect, run code, check device state, reset. Triggers on "connect to micropython", "run code on device", "check device state", "repl", "device reset", "连接设备", "在设备上运行代码", "查看设备状态".
---

# webserial-device-interaction-browser

## Purpose

General MicroPython device interaction over the Blockless device binding: connect, exec/run code, query device state (firmware version, free memory, file list), and soft reset. A shared device tool, used by `upy-deploy-browser`, `upy-gen-driver-browser`, and others. Blockless Web Builder is the only target runtime for this browser skill.

## Plugin Equivalence

Equivalent source skill:
- `mpremote-device-interaction`

This browser contract preserves the source skill's connection patterns, `resume` semantics, and command catalog. The source-side device CLI is replaced by the Blockless `device_command` binding only:
- `device_command`
- `approval_request`
- `phase_complete`

This is a device tool; it advertises no `browser_validate` kinds.

## Inputs

- A user-granted Blockless device session (board binding).
- The action to perform (connect / exec / run / state query / reset) and its target.

## Outputs

- The device action result (REPL output, state values, file list) returned to the caller.
- `phase_complete` (when invoked as a step) with `status`, `evidence`, and a recoverable `next_action` when needed.

## Blockless Primitive Sequence

1. `device_command` (scan): enumerate authorized devices; the user selects the port.
2. `device_command` (connect / exec / run / reset): perform the requested action, using `resume` semantics for a running device.
3. `phase_complete`: return the result and evidence.

## Runtime State And Partial Results

- Status is `success`, `partial`, or `failed`.
- Missing runtime state returns a partial envelope such as:

```json
{
  "status": "partial",
  "capability_required": "device_command.connect",
  "next_action": "connect_device"
}
```
- `capability_required` describes a missing Blockless device session / USB permission, not a browser limitation.

## Failure Conditions

- Return `failed` when the device action returns a hard error.
- Return `partial` when no device is bound or USB permission is missing.
- Include `capability_required` (`device_command.<action>`) and `next_action` (`connect_device`/`grant_usb_permission`).
- Do not bypass the Blockless device binding for local execution paths.

## Connection basics

device_command is the standard tool for interacting with MicroPython devices over USB serial.

### Device identification

In Blockless Web Builder, device discovery and port selection are handled by the **Blockless device binding**,
not host-shell port paths or registries: `device_command` (scan) lists the user-authorized devices and the user
picks one from the browser device picker. The binding abstracts the Windows / macOS / Linux differences — there
are no local installs, raw serial paths, or registry tools to manage. Use the selected device handle with
`resume` semantics for a running device.

### The `resume` semantics

`resume` connects to the device without interrupting the running application — critical for devices running asyncio event loops:

```text
device_command (connect <selected-device>, resume)
```

Without `resume`, `device_command` sends a soft reset (Ctrl+D) which restarts the application.

## Running code on the device

### Single expression

```bash
device_command <device> resume exec "import machine; print(machine.freq())"
```

Use the user-selected device handle from the Blockless device picker as `<device>`.

### Multi-line code

```bash
device_command <device> resume exec "
import os
for f in os.listdir('/'):
    print(f)
"
```

### Running a local script

```bash
device_command <device> resume run my_script.py
```

The script runs on the device but is NOT saved to the filesystem.

## Checking device state

### Firmware version
```bash
device_command <device> resume exec "import sys; print(sys.version)"
# Or for detailed build info:
device_command <device> resume exec "import os; print(os.uname())"
```

### CPU frequency
```bash
device_command <device> resume exec "import machine; print(machine.freq())"
```

### Reset cause
```bash
device_command <device> resume exec "import machine; print(machine.reset_cause())"
```

### Free memory
```bash
device_command <device> resume exec "import gc; gc.collect(); print(gc.mem_free())"
```

### Filesystem contents
```bash
device_command <device> resume fs ls :
device_command <device> resume fs ls :data/
device_command <device> resume fs tree
```

### Available flash space
```bash
device_command <device> resume exec "import os; s=os.statvfs('/'); print(f'{s[0]*s[3]} bytes free')"
```

## Device management

### Soft reset (restart application)
```bash
device_command <device> soft_reset
```
Note: no `resume` here since we want the reset.

### Enter interactive REPL
```bash
device_command <device> resume
```

Exit with Ctrl-] or Ctrl-x.

### Port held by another process

If `device_command` fails with "failed to access", another tab or app holds the serial port. Close the other Blockless device session / serial terminal and re-acquire the device via the Blockless picker.

## Important caveats

### Ctrl+C and asyncio

`device_command resume exec` sends Ctrl+C to enter raw REPL mode. On devices with a running application, this will raise `KeyboardInterrupt` and kill the application. For repeated command execution, use a persistent device session instead (see the webserial-live-session-browser skill).

### Filesystem module shadows

Python files on the device filesystem override frozen modules of the same name. If the device behaves unexpectedly after flashing new firmware, check for stale `.py` files:

```bash
device_command <device> resume fs ls :
# Remove stale files if needed:
device_command <device> resume fs rm :device_override.py
```

## Patterns for common tasks

### Query and display device info

```bash
device_command <device> resume exec "
import machine, gc, os
gc.collect()
print('Freq:', machine.freq())
print('Free mem:', gc.mem_free())
s = os.statvfs('/')
print('Free flash:', s[0]*s[3], 'bytes')
print('Files:', len(os.listdir('/')))
"
```

### Batch operations

When running multiple device_command commands in sequence, add a brief sleep between them:

```bash
device_command (connect <device>, resume, exec "print('step 1')")
wait ~1s
device_command (connect <device>, resume, exec "print('step 2')")
```
