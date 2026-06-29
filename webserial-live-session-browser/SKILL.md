---
name: webserial-live-session-browser
description: Maintain a persistent interactive device session over the Blockless device binding inside Blockless Web Builder — send command sequences and capture output over time. Preferred when multiple commands are needed, monitoring output over time, or the device runs an asyncio event loop with aiorepl. Triggers on "send commands to device", "monitor device output", "interactive session", "persistent connection", "stress test device", "capture serial output", "持续监听设备", "长连接设备", "监控串口输出".
---

# webserial-live-session-browser

## Purpose

Maintain a persistent interactive device session over the Blockless device binding to send command sequences and capture output over time — the preferred approach for asyncio/aiorepl devices, stress tests, and long monitoring. A shared device tool, used by `upy-deploy-browser` and others. Blockless Web Builder is the only target runtime for this browser skill.

## Plugin Equivalence

Equivalent source skill:
- `mpremote-live-session`

This browser contract preserves the source skill's persistent-session rationale, the "never repeatedly send Ctrl+C to an asyncio device" rule, and output-capture patterns. The source-side device CLI / PTY session is replaced by the Blockless `device_command` persistent session only:
- `device_command`
- `phase_complete`

Validation kinds retained for this skill:
- `device_test_plan`

## Inputs

- A user-granted Blockless device session.
- The command sequence / monitoring duration, or a device test plan.

## Outputs

- The captured session output (REPL stream, monitored values).
- `phase_complete` (when invoked as a step) with `status`, `evidence`, and a recoverable `next_action` when needed.

## Blockless Primitive Sequence

1. `browser_validate` (`device_test_plan`): validate the test/monitor plan when one is supplied.
2. `device_command` (open persistent session): connect with `resume` and hold the session open.
3. `device_command` (stream): send commands and capture output over time without re-entering raw REPL.
4. `phase_complete`: return the captured output and evidence.

## Runtime State And Partial Results

- Status is `success`, `partial`, or `failed`.
- Missing runtime state returns a partial envelope such as:

```json
{
  "status": "partial",
  "capability_required": "device_command.stream",
  "next_action": "connect_device"
}
```
- `capability_required` describes a missing Blockless device session / USB permission, not a browser limitation.

## Failure Conditions

- Return `failed` when the session cannot be established or the device returns a hard error.
- Return `partial` when no device is bound or USB permission is missing.
- Include `capability_required` (`device_command.<action>`) and `next_action` (`connect_device`/`grant_usb_permission`).
- Do not bypass the Blockless device binding for local execution paths.

## CRITICAL: Never use repeated `device_command resume exec` calls

Each `device_command resume exec` invocation sends Ctrl+C to enter raw REPL mode. On devices running an asyncio event loop, this raises `KeyboardInterrupt` which is a `BaseException` — not caught by asyncio's `except (CancelledError, Exception)` handler. This kills the event loop, leaving the device in a zombie state where C-level tasks (SPI, GC, timers) continue but no Python asyncio task runs.

**Always use a persistent session instead.**

## Platform support

The persistent session is held open by the Blockless `device_command` binding inside Blockless Web Builder. The runtime owns the serial transport (WebSerial under the hood), so there is no host PTY, `pyserial`, or subprocess to manage and no Linux/macOS/Windows split — the same `device_command` session operations work on every platform. There are no raw serial paths or local terminal emulation in this skill.

## Opening the persistent session

Open the session once with `resume` (so a running asyncio app is not interrupted) and hold it open for the whole interaction instead of issuing a fresh `device_command resume exec` per command:

```text
session = device_command (connect <selected-device>, resume, mode=stream)
```

`<selected-device>` is the handle returned by the Blockless device picker (`device_command` scan). The open session enters the aiorepl prompt (text input), not raw REPL — so no Ctrl+C is sent and the event loop survives.

## Sending commands over the session

Stream each command line into the open session; the aiorepl prompt accepts raw text. Send the command, then read the output it produces before sending the next one:

```text
session.send("import sys; print(sys.version)")   # stream a command line into the session
wait ~0.3s                                        # let aiorepl process
output = session.read(timeout ~1s)                # capture what the device emitted
```

## Reading output over time

`session.read` captures whatever the device has emitted without blocking — return as soon as the device goes quiet for the timeout window. This is how you monitor output across many cycles without re-entering raw REPL:

```text
loop while monitoring:
    chunk = session.read(timeout ~0.1s)   # non-blocking capture
    if chunk is empty: keep waiting
    else: append chunk and record last_output_time
```

## Logging the captured output

Accumulate the chunks and return the captured transcript as `phase_complete` evidence. Do not tee to a host log file; there is no host filesystem in this target, and this skill returns its stream through the phase envelope, not a local file.

## Closing the session

End the session explicitly when finished so the device binding releases the serial port for the next caller:

```text
session.close()   # device_command releases the binding; no host process to kill
```

If you skip this, a later `device_command` may fail with "failed to access" because the port is still held.

## When to use this vs device_command exec

| Scenario | Approach |
|---|---|
| Single quick query | `device_command <device> resume exec "print(...)"` |
| Multiple commands over time | Persistent session |
| Monitoring device output | Persistent session |
| Device runs asyncio/aiorepl | Persistent session (REQUIRED) |
| Stress testing | Persistent session |
| File copy operations | Direct `device_command <device> resume fs cp` |

## The `resume` subcommand

Always use `resume` when connecting to a running device. Without it, device_command performs a soft reset which restarts the application:

```
device_command connect <device> resume        # Correct: connects without interrupting
device_command connect <device>               # WRONG: soft resets the device
```

## aiorepl vs raw_repl

MicroPython devices with asyncio typically run aiorepl, which provides an interactive REPL integrated with the asyncio event loop. Two modes:

- **aiorepl prompt** (typing text): Commands execute within the running event loop. No Ctrl+C sent. Safe for asyncio devices. The persistent session uses this mode.
- **raw_repl** (Ctrl+A protocol): Used by `device_command exec`. Sends Ctrl+C first, which can kill the event loop.

## Detecting stalls

Monitor `last_output_time` to detect when the device stops producing output:

```python
STALL_TIMEOUT = 45  # seconds
last_output_time = time.time()

def is_stalled():
    return time.time() - last_output_time > STALL_TIMEOUT
```
