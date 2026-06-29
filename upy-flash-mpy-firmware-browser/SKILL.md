---
name: upy-flash-mpy-firmware-browser
description: Phase — MicroPython firmware resolve, download, flash, or manual-confirm, inside Blockless Web Builder. Consumes the select-hw manifest, resolves the latest firmware from micropython.org/download, flashes ESP32 over WebSerial, guides Pico UF2 copy, or shows manual links for other boards, then hands off to upy-scaffold-browser.
---

# upy-flash-mpy-firmware-browser

## Purpose

Consume the select-hw `manifest_content`, resolve the latest MicroPython firmware from micropython.org/download, and put the interpreter firmware on the board: flash ESP32 over the Blockless device binding (WebSerial), guide the Pico UF2 copy, or present manual instructions for other boards. This phase does not re-analyze requirements, re-select the board, or generate business code. Blockless Web Builder is the only target runtime for this browser skill.

## Plugin Equivalence

Equivalent source skill:
- `upy-flash-mpy-firmware-plugin`

This browser contract preserves the source skill's board-family branching (ESP32 / Pico / Manual), firmware-resolution flow, user-confirmation gates, failure states, and phase handoff. Source-side local toolchain bootstrap and serial-flasher tooling are replaced by Blockless primitives only:
- `approval_request`
- `file_operation`
- `device_command`
- `browser_validate`
- `phase_complete`

Validation kinds retained for this phase:
- `firmware_page_resolve`
- `firmware_download`
- `firmware_flash_plan`
- `firmware_flash_execute`
- `uf2_manual_confirm`

## Inputs

- Blockless project id, project store snapshot, and the select-hw `manifest_content` (board name, chip family, firmware port).
- A user-granted Blockless device session when ESP32 serial flashing is required.
- Validation inputs for: `firmware_page_resolve`, `firmware_download`, `firmware_flash_plan`, `firmware_flash_execute`, `uf2_manual_confirm`.

## Outputs

- artifacts/firmware-flash-plan.json plus the resolved firmware reference and flash/confirm result in the project store.
- `phase_complete` for `flash_firmware` with `status`, `evidence`, `artifacts`, `next_phase` (`upy-scaffold-browser`), and a recoverable `next_action` when needed.

## Blockless Primitive Sequence

1. `file_operation`: read the select-hw manifest.
2. `browser_validate` (`firmware_page_resolve`): resolve the board's MicroPython download page + latest firmware file (returns `partial` until a firmware provider is loaded).
3. `browser_validate` (`firmware_download`): fetch the resolved firmware artifact.
4. `browser_validate` (`firmware_flash_plan`): build the flash plan for the board branch (see below).
5. `approval_request`: confirm before mutating device state — flashing only proceeds after explicit user confirmation.
6. Per board branch: `device_command` + `browser_validate` (`firmware_flash_execute`) for ESP32 serial flash; `uf2_manual_confirm` for Pico UF2; `approval_request` manual confirm for other boards.
7. `phase_complete`: hand off to `upy-scaffold-browser`.

## 板卡分支

| 分支 | 条件 | 行为 |
| --- | --- | --- |
| ESP32 | `firmware_board_name` 以 `ESP32_` 开头、`firmware.port == "esp32"`，或 `chip_family` 以 `esp32` 开头 | `firmware_page_resolve` 解析最新 `.bin` 与安装命令；`device_command`（scan）扫描并由用户选择真实串口；**只在用户 `approval_request` 确认后**用 `device_command` + `firmware_flash_execute` 经 WebSerial 烧录。 |
| Pico | `firmware_board_name` 以 `RPI_PICO` 开头 | `firmware_page_resolve` 解析最新 `.uf2`；提示用户断开 USB、按住 BOOTSEL 重连、把 UF2 复制到 `RPI-RP2` 磁盘；用 `uf2_manual_confirm` 等待用户确认 `copied_uf2`。 |
| Manual | 其他 MicroPython 板卡 | 只解析 MicroPython 下载/安装链接并展示手动烧录说明，用 `approval_request` 等待用户确认。不替用户执行任何本地烧录工具。 |

**串口选择**：真实运行必须用 `device_command`（scan）枚举真实串口并由用户选择；只有 mock/sample 测试可用固定串口（如 Windows `COM3`、Linux `/dev/ttyUSB0`、macOS `/dev/cu.usbmodem1101`）做 JSON 与命令规划校验。

## 固件解析规则（板卡事实）

只从 select-hw 的 `phase_complete.payload.manifest_content` 读取板卡事实，字段优先级如下：

| 取值 | 优先来源 | 兜底来源 |
| --- | --- | --- |
| 固件 URL | `hardware_selection.selected_board.firmware.url` | `mcu.firmware_url`；都缺失才用固件板卡名到下载索引匹配真实下载页 |
| 固件板卡名 | `hardware_selection.selected_board.firmware.board_name` | `mcu.firmware_board_name` |
| 固件 port | `hardware_selection.selected_board.firmware.port` | 从板卡名推断 |
| 芯片族 | `hardware_selection.selected_board.chip_family` | `mcu.chip_family` |
| 展示名称 | `hardware_selection.selected_board.display_name` | `mcu.display_name` |

**解析硬规则**（由 `firmware_page_resolve` 执行，但本 skill 必须遵循）：

- **不要信任缓存的 `latest_version`**：必须优先用上游 `firmware.url`（其次 `mcu.firmware_url`）访问 MicroPython 官方板卡页解析真实 `(latest)` 固件与安装说明。
- 仅当上游 URL 缺失/无效时，才用 `firmware_board_name` 到 `https://micropython.org/download/` 首页匹配真实下载页 slug。
- **不要**用 `display_name`、`board_id` 或 MCU 型号直接拼下载 URL（它们仅用于展示/本地库 ID）。
- `download_slug` = 从固件 URL path 提取或从下载首页匹配出的真实下载页 slug；`board_url` = 规范化后的板卡页 URL。

## Pico UF2 流程

`firmware_page_resolve` 解析最新 `.uf2` 后，用 `approval_request` 展示步骤并等待 `copied_uf2`：

```
断开 Pico USB → 按住 BOOTSEL 重连 → 把 UF2 复制到 RPI-RP2 磁盘 → 等待开发板自动重启
```

用户确认 `copied_uf2` 即视为成功。跨平台挂载路径仅作提示，不改变手动复制契约，也不得因未找到挂载点就自动判失败（除非用户也未确认 `copied_uf2`）：

- Windows：卷标 `RPI-RP2` 的可移动磁盘。
- macOS：`/Volumes/RPI-RP2`。
- Linux：`/media/$USER/RPI-RP2`、`/run/media/$USER/RPI-RP2` 或 `/mnt/RPI-RP2`。

## 手动板卡流程

对非 ESP32/Pico 板卡，只解析 MicroPython 板卡链接并展示手动说明，用 `approval_request`（`approval_id="manual_firmware_flash_confirm"`）等待用户确认。不替用户执行任何本地烧录工具提示。

## Runtime State And Partial Results

- `phase_complete.status` is `success`, `partial`, or `failed`.
- `phase_complete.next_phase` is `upy-scaffold-browser` on success.
- Missing runtime state returns a partial envelope such as:

```json
{
  "status": "partial",
  "phase": "flash_firmware",
  "capability_required": "browser_validate.firmware_page_resolve",
  "next_action": "load_provider"
}
```
- For ESP32 with no connected board / USB permission, `capability_required` is `device_command.flash` with `next_action` `connect_device` or `grant_usb_permission`. These describe missing Blockless device/provider state, not a browser limitation.

## Failure Conditions

- Return `failed` when firmware resolution finds no firmware for the board, or the ESP32 flash reports a hard error.
- Return `partial` when the firmware provider, connected board, USB permission, or user confirmation is missing — these are recoverable.
- Include `capability_required` (`browser_validate.<kind>` / `device_command.<action>`) and `next_action` (`load_provider`/`connect_device`/`grant_usb_permission`/`sign_in`).
- Do not bypass Blockless primitives for local execution paths; never auto-run a board flasher without explicit user confirmation.

## Domain Flashing vs browser_validate (boundary)

Board-branch decisions and user guidance are the LLM's job; firmware resolution/download/flash go through `browser_validate` (`firmware_*`) and `device_command`. `browser_validate` performs only the objective subset (resolve / download / plan / flash-execute / uf2-confirm). The "flash only after explicit confirmation" gate is mandatory. Blockless Web Builder runs both.
