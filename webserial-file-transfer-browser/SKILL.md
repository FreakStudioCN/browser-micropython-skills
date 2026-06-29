---
name: webserial-file-transfer-browser
description: Copy files between the Blockless project store and a MicroPython device over the device binding (device_command) inside Blockless Web Builder — cp, ls, mkdir, rm, tree. Triggers on "copy file to device", "upload to device", "download from device", "device filesystem", "copy firmware files", "上传文件到设备", "从设备下载文件", "同步文件".
---

# webserial-file-transfer-browser

## Purpose

Copy files between the Blockless project store and the MicroPython device over the Blockless device binding, and manage the device filesystem (cp, ls, mkdir, rm, tree). A shared device tool, used by `upy-deploy-browser` and others. Blockless Web Builder is the only target runtime for this browser skill.

## Plugin Equivalence

Equivalent source skill:
- `mpremote-file-transfer`

This browser contract preserves the source skill's transfer recipes, `resume` rule, and filesystem operations. The source-side device CLI is replaced by the Blockless `device_command` binding only:
- `device_command`
- `file_operation`
- `phase_complete`

Validation kinds retained for this skill:
- `project_files`

## Inputs

- A user-granted Blockless device session.
- The transfer action (cp to/from, ls, mkdir, rm, tree) and its source/target paths.

## Outputs

- The transfer result (copied files, directory listing) and any pulled files written to the project store.
- `phase_complete` (when invoked as a step) with `status`, `evidence`, and a recoverable `next_action` when needed.

## Blockless Primitive Sequence

1. `browser_validate` (`project_files`): confirm target paths are project-relative.
2. `device_command` (fs cp / ls / mkdir / rm / tree): perform the transfer, using `resume` semantics so the device is not soft reset mid-transfer.
3. `file_operation`: persist any pulled files into the project store.
4. `phase_complete`: return the result and evidence.

## Runtime State And Partial Results

- Status is `success`, `partial`, or `failed`.
- Missing runtime state returns a partial envelope such as:

```json
{
  "status": "partial",
  "capability_required": "device_command.cp",
  "next_action": "connect_device"
}
```
- `capability_required` describes a missing Blockless device session / USB permission, not a browser limitation.

## Failure Conditions

- Return `failed` when the transfer returns a hard error or a path is invalid.
- Return `partial` when no device is bound or USB permission is missing.
- Include `capability_required` (`device_command.<action>` / `browser_validate.project_files`) and `next_action`.
- Do not bypass the Blockless device binding for local execution paths.

## Basic copy operations

Copy a local file to the device:
```bash
device_command <device> resume fs cp local_file.py :remote_file.py
```

Copy from device to host:
```bash
device_command <device> resume fs cp :remote_file.py local_file.py
```

The colon prefix `:` denotes a device path. Without it, the path is local.

## Always use `resume`

```bash
device_command <device> resume fs cp file.py :file.py     # Correct: no soft reset
device_command <device> fs cp file.py :file.py             # WRONG: resets device first
```

Without `resume`, device_command performs a soft reset before the filesystem operation, restarting the application and potentially losing state.

## Device path by platform

### Windows

```bash
# Discover port
device_command connect list

# Copy using shortcut or explicit COM port
device_command c3 resume fs cp main.py :main.py
device_command connect COM3 resume fs cp main.py :main.py
```

### macOS / Linux

```bash
# Discover authorized devices (the Blockless picker abstracts the OS port path)
device_command connect list

# Copy using the selected device handle
device_command connect <selected-device> resume fs cp main.py :main.py
```

### Device selection

The device handle comes from the Blockless device picker (`device_command` scan + user authorization) — no host port paths or registry tools:

```text
device_command (connect <selected-device>, resume, fs cp file.py :file.py)
```

A device's port identity can change on reconnection — re-select it from the Blockless picker instead of reusing a stale handle.

## Device path syntax

- `:filename.py` - file in the device's current directory (root)
- `:/path/to/file` - absolute path on device
- `:data/1.data` - relative path on device

## Directory operations

List files:
```bash
device_command <device> resume fs ls :
device_command <device> resume fs ls :data/
```

Create directory:
```bash
device_command <device> resume fs mkdir :data
```

Remove file:
```bash
device_command <device> resume fs rm :device_override.py
```

Remove directory (must be empty):
```bash
device_command <device> resume fs rmdir :old_dir
```

Recursive file tree:
```bash
device_command <device> resume fs tree
```

## Copying multiple files

device_command processes one operation per invocation. For multiple files, iterate over them:

```text
# Loop: copy each .py with a brief pause between transfers
for each .py file:
    device_command (connect <device>, resume, fs cp <file> :<file>)
    wait ~500ms
```

The brief pause is important — device_command holds the serial port during the copy and the next invocation needs it released.

## Large file transfers

For files >50KB, the transfer takes several seconds. device_command uses the raw REPL protocol for `fs cp`, which sends Ctrl+C on entry. On asyncio/aiorepl devices, this can crash the event loop.

For large transfers to asyncio devices, consider:
1. Transfer while the device is in a safe state (e.g. on dock, not collecting data)
2. Accept that the transfer may restart the application
3. Use the persistent session approach for very large batch transfers (see webserial-live-session-browser skill)

## Filesystem capacity

Check available space:
```bash
device_command <device> resume exec "import os; print(os.statvfs('/'))"
```

The result tuple fields: `(bsize, frsize, blocks, bfree, ...)`. Available bytes = `bsize * bfree`.

## Common patterns

### Driver development workflow: update + restart + monitor

```bash
# Linux/macOS
device_command <device> resume fs cp utils/driver.py :utils/driver.py + soft_reset repl

# Windows PowerShell
device_command connect COM3 resume fs cp utils/driver.py :utils/driver.py + soft_reset repl
```

### Deploy a Python module and reboot

```bash
device_command <device> resume fs cp device_override.py :device_override.py
device_command <device> resume fs ls :
device_command <device> resume exec "import machine; machine.reset()"
```

### Recursive directory sync

```bash
device_command <device> resume fs cp -r utils/ :utils/ + soft_reset repl
```

### Back up device data into the project store

```text
# List the device data files, then pull each into the project store
files = device_command (connect <device>, resume, fs ls :data/)
for each file in files:
    device_command (connect <device>, resume, fs cp :data/<file> <local>)
    file_operation (write backup/data/<file> from the pulled bytes)
    wait ~500ms
```

Pulled files land in the Blockless project store via `file_operation` — there is no host backup directory in this target.

### Clean device filesystem

```bash
device_command <device> resume exec "
import os
for f in os.listdir('data'):
    os.remove('data/' + f)
    print('removed', f)
"
```

## Troubleshooting

**"failed to access" / port in use**: another tab or app holds the port; close the other Blockless device session / serial terminal and re-acquire the device via the Blockless picker.

**Port in use (Windows)**: Close Thonny, PuTTY, Arduino IDE, or any other serial terminal that may hold the COM port.

**Transfer seems to hang**: Large files take time. A 70KB file takes ~3 seconds. Don't interrupt — partial writes corrupt the filesystem.

**File appears but content is wrong**: After writing, either reboot or call `os.sync()` from the REPL.
