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
2. `approval_request` (`firmware_action_select`): if no `firmware_action` is supplied, ask the user which operation to run (`download_and_flash` / `download_only` / `already_flashed` / `use_local_firmware` / `save_partial` / `cancel` — see below).
3. `browser_validate` (`firmware_page_resolve`): resolve the board's MicroPython download page + latest firmware file (returns `partial` until a firmware provider is loaded).
4. `browser_validate` (`firmware_download`): fetch the resolved firmware artifact.
5. `browser_validate` (`firmware_flash_plan`): build the flash plan for the board branch — parsed erase/write commands + `write_offset` (see below).
6. `approval_request` (`esp32_flash_confirm` / `manual_firmware_flash_confirm`): confirm before mutating device state — flashing only proceeds after explicit user confirmation.
7. Per board branch: `device_command` + `browser_validate` (`firmware_flash_execute`) for ESP32 serial flash; `uf2_manual_confirm` for Pico UF2; `approval_request` manual confirm for other boards.
8. `phase_complete`: hand off to `upy-scaffold-browser`.

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
| 烧录工具提示 | `mcu.flash_tool` | 从板卡族推断 |
| 展示名称 | `hardware_selection.selected_board.display_name` | `mcu.display_name` |

**解析硬规则**（由 `firmware_page_resolve` 执行，但本 skill 必须遵循）：

- **不要信任缓存的 `latest_version`**：必须优先用上游 `firmware.url`（其次 `mcu.firmware_url`）访问 MicroPython 官方板卡页解析真实 `(latest)` 固件与安装说明。
- 仅当上游 URL 缺失/无效时，才用 `firmware_board_name` 到 `https://micropython.org/download/` 首页匹配真实下载页 slug。
- **不要**用 `display_name`、`board_id` 或 MCU 型号直接拼下载 URL（它们仅用于展示/本地库 ID）。
- `download_slug` = 从固件 URL path 提取或从下载首页匹配出的真实下载页 slug；`board_url` = 规范化后的板卡页 URL。

若主来源与兜底来源都缺失，必须 fail-loud（`structured_error.code="missing_firmware_url"`），不要静默继续或自己拼 URL。

## firmware_action 用户操作选择（approval_request）

下载或烧录任何固件前，如果上游/输入没有给定 `firmware_action`，必须先发 `approval_request`（`approval_id="firmware_action_select"`）让用户选择本阶段操作。动作取值与语义：

| 动作 | 含义 |
| --- | --- |
| `download_and_flash` | 下载最新固件并烧录（主动作）。 |
| `download_only` | 只下载固件，不烧录；`firmware.status="partial_download_only"`。 |
| `already_flashed` | 用户已自行烧录，跳过；输出 `success` 且 `firmware.status="skipped_user_confirmed"`。 |
| `use_local_firmware` | 使用用户提供的本地固件文件（`firmware_override.local_path`），不再解析下载。 |
| `save_partial` | 稍后继续；输出带 checkpoint 的 `partial`。 |
| `cancel` | 取消；输出带 checkpoint 的 `partial`。 |

若 `approval_request` 的 UI 一次只能展示有限选项，优先展示 4 个主动作（`download_and_flash` / `download_only` / `already_flashed` / `use_local_firmware`），`save_partial` 与 `cancel` 通过二次确认或后续 checkpoint 处理。审批超时按 `save_partial` 处理（`partial` + checkpoint），不要静默默认烧录。

## ESP32 烧录细节与 `esp32_flash_confirm` 审批

必须先用 `browser_validate` (`firmware_page_resolve`) 解析 MicroPython 板卡页的安装说明，再用 `browser_validate` (`firmware_flash_plan`) 生成擦除/写入计划。**不要把硬编码 offset 作为主要来源**：例如 `ESP32_GENERIC_C5` 当前使用 `write_flash 0x2000`，所以固定整个 C 系列的 offset 是错误的。`write_offset` 必须使用页面解析到的命令参数原值（如 `"0"`），**不要在同一阶段内混用 `"0"` 和 `"0x0"`**。

烧录前的 `approval_request`（`approval_id="esp32_flash_confirm"`）必须包含：

- 固件文件名和 MicroPython 板卡页面。
- 从页面解析出的擦除/写入命令和 `write_offset`。
- `device_command`（scan）扫描到的真实串口选项。
- 下载模式提示：通常按住 **BOOT**，按 **EN/RESET**，再松开 **BOOT**；如果板卡说明不同，提醒用户按板卡说明操作。
- 明确警告：烧录会擦除并重写 MicroPython 固件。

用户确认（携带所选 `serial_port` 与 `baud`，如 `460800`）后，才用 `device_command` + `browser_validate` (`firmware_flash_execute`) 经 WebSerial 执行擦除/写入。烧录成功后 `flash_result` 至少记录 `port`、`baud`、`chip`、统一的 `write_offset`、`erased_first` 与日志证据。

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

手动烧录审批（`manual_firmware_flash_confirm`）字段含义：

| 字段 | 含义 |
| --- | --- |
| `summary.board_name` | 上游固件板卡名。 |
| `summary.firmware_page` | MicroPython 官方板卡页 URL。 |
| `summary.latest_firmware_url` | 页面中标记为 latest 的主固件链接。 |
| `summary.latest_version` / `summary.latest_date` | latest 固件版本与日期（如 `v1.28.0` / `2026-04-06`）。 |
| `summary.file_type` | 固件类型枚举：`dfu` / `uf2` / `bin` / `hex` / `zip`。 |
| `summary.flash_method` | 固定为 `manual`。 |
| `summary.tool_hint` | 页面说明提取的工具/方式：`dfu-util` / `st-flash` / `uf2-drag-drop` / `teensy-loader` / `ftp-copy` / `manual`。 |
| `links[]` / `steps[]` / `warnings[]` | 下载/文档链接、面向用户的中文步骤、风险提示。 |
| `commands[]` | 可选；只展示页面命令，**每项必须标记 `execute_allowed=false`，浏览器端绝不自动执行**。 |
| `actions[]` | `confirm_flashed` / `save_partial` / `cancel`。 |

## `firmware.status` 结果取值

`phase_complete.payload.firmware.status` 取值（结果判定模型）：

```text
downloaded
flashed
uf2_copied
manual_confirmed
skipped_user_confirmed
partial_download_only
failed
```

`partial` 与 `failed` 时 `next_phase` 必须为 null。

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

## 断点与结构化错误

`partial` / `failed` 且可恢复时，写入 checkpoint 标明 `resume_step`（恢复点分类）：

```text
load_upstream_select_hw
select_firmware_action
resolve_firmware_page
download_firmware
scan_serial_ports
confirm_esp32_flash
run_esp32_flash
wait_pico_uf2_copy
manual_firmware_flash_confirm
phase_complete_validation
```

结构化错误字段：`code`（稳定机器可读错误码）、`message`（面向用户，优先中文）、`severity`（`info` / `warning` / `error` / `fatal`）、`recoverable`（能否恢复）、`retryable`（能否同参重试）、`source`（出错的步骤/校验）、`field`（可选 JSON 字段路径）。建议错误码：

```text
invalid_upstream_phase
missing_firmware_url
firmware_page_lookup_failed
latest_firmware_not_found
download_failed
user_saved_partial
user_cancelled
serial_port_missing
flash_execute_failed
pico_copy_not_confirmed
manual_flash_not_confirmed
artifact_missing
phase_complete_invalid
```

错误必须 fail-loud：缺少固件 URL、解析失败、下载失败、未选串口等，按上表输出结构化错误并停在可恢复 checkpoint，不要静默跳过或伪造成功。

## Domain Flashing vs browser_validate (boundary)

Board-branch decisions and user guidance are the LLM's job; firmware resolution/download/flash go through `browser_validate` (`firmware_*`) and `device_command`. `browser_validate` performs only the objective subset (resolve / download / plan / flash-execute / uf2-confirm). The "flash only after explicit confirmation" gate is mandatory. Blockless Web Builder runs both.
