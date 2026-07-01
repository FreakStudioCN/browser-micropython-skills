---
name: upy-select-hw-browser
description: Phase 2 — MCU selection + firmware verification + pin allocation + BOM, inside Blockless Web Builder. Consumes the analyze manifest and produces the full hardware plan. Triggers after upy-analyze-browser.
---

# upy-select-hw-browser

## Purpose

From the analyze manifest (devices + requirements + mcu_specified), perform MCU selection, MicroPython-firmware verification, pin allocation, and BOM generation. Writes no code and handles no drivers. The selection/allocation is performed by the LLM applying the rules below; `browser_validate` validates the hardware manifest. Blockless Web Builder is the only target runtime for this browser skill.

## Plugin Equivalence

Equivalent source skills:
- `upy-select-hw`
- `upy-select-hw-plugin`

This browser contract preserves the source skill's responsibility, MCU/pin rules, firmware mapping, BOM rules, and failure semantics. Source-side local firmware/flash tooling references are replaced by Blockless primitives only:
- `file_operation`
- `approval_request`
- `browser_validate`
- `phase_complete`

Validation kinds retained for this phase:
- `select_hw_manifest` (includes chip-fact pin sanity: rejects reserved/input-only/non-exposed pins)
- `manifest_phase`

## Inputs

- Blockless project id, project store snapshot, and the analyze `manifest_content`.
- Validation inputs for: `select_hw_manifest`, `manifest_phase`.

## Outputs

- artifacts/select-hw-manifest.json — the hardware plan (mcu + pin allocation + BOM).
- `phase_complete` for `select_hw` with `status`, `evidence`, `artifacts`, `next_phase` (`upy-flash-mpy-firmware-browser`), and a recoverable `next_action` when needed.

## Blockless Primitive Sequence

1. `file_operation`: read the analyze manifest.
2. Select MCU + allocate pins + build BOM per the rules below (LLM-driven; see the domain/validate boundary section).
3. `approval_request`: confirm the board choice when not user-specified.
4. `file_operation`: write the hardware plan (mcu + pinout + bom) to `project-manifest.json` **before** validating (the validators read the written snapshot).
5. `browser_validate` (`select_hw_manifest`, `manifest_phase`): validate the written hardware manifest.
6. `phase_complete`: hand off to `upy-flash-mpy-firmware-browser`.

## Runtime State And Partial Results

- `phase_complete.status` is `success`, `partial`, or `failed`.
- `phase_complete.next_phase` is `upy-flash-mpy-firmware-browser` on success.
- Missing runtime state returns a partial envelope such as:

```json
{
  "status": "partial",
  "phase": "select_hw",
  "capability_required": "browser_validate.select_hw_manifest",
  "next_action": "load_provider"
}
```
- `capability_required` describes missing Blockless runtime state or provider registration, not a browser limitation.

## Failure Conditions

- Return `failed` when the input manifest is malformed, no MPY firmware is verifiable, or pin allocation conflicts cannot be resolved.
- Return `partial` when a required Blockless provider, project-store access, or user confirmation is missing.
- Include `capability_required` (`browser_validate.<kind>`) and `next_action` (`load_provider`/`sign_in`).
- Do not bypass Blockless primitives for local execution paths.

## Domain Selection vs browser_validate (boundary)

MCU recommendation, firmware verification, and pin allocation are the LLM's job. `browser_validate` performs only the objective subset — hardware-manifest validation (`select_hw_manifest`/`manifest_phase`), where `select_hw_manifest` also enforces chip-fact pin sanity (rejects reserved/input-only/non-exposed pins). It does **not** choose the board. Blockless Web Builder runs both.

## 角色定位

给定 `project-manifest.json`（devices + requirements + mcu_specified），完成 MCU 选型、固件核验、引脚分配、BOM 生成。**不写代码，不管驱动。**

## 前置检查

无需本地环境：选型与校验通过 `browser_validate`（`select_hw_manifest`/`manifest_phase`）完成。

---

## 执行步骤

### Step 1: MCU 选型 + 固件核验

#### 情况 A：用户已指定 MCU（`mcu_specified` 有值）

```
1. 核验 MicroPython 固件是否支持：

   已知支持型号 → 直接通过（见下表）
   非常见型号 → WebSearch: site:micropython.org/download {型号}
   
   无固件 → 停止！告知用户并建议替代：
     ESP32 (最通用) / Pico (性价比) / ESP32-S3 (AI 能力)

2. 输出固件下载链接：
   URL: https://micropython.org/download/{BOARD_NAME}/
```

#### 情况 B：用户未指定 MCU → LLM 推荐

**推荐策略：优先 Pico 系列和 ESP32 系列（MPY 适配最好）。**

```
打分逻辑：

  需要 WiFi/BLE     → +1 ESP32 系列, +1 Pico W
  需要 AI/语音/摄像头 → +1 ESP32-S3
  低功耗 + 电池供电   → +1 ESP32-C3
  纯 GPIO 控制       → +1 Pico 系列
  极致低价           → +1 ESP8266 / Pico
  新手入门           → +1 Pico (USB 拖拽烧录) / ESP32

  最终推荐 Top 1，附简短理由。

  备选：Top 2（用户可切换）
```

**推荐输出示例：**

```
推荐主控：Raspberry Pi Pico W
  理由：需要 WiFi（requirements.network=wifi），RP2040 性价比高，
        MPY 适配极好，USB 拖拽烧录对新手友好。

备选：ESP32（WiFi + BLE，生态最全，接口更多）

确认使用哪个？或者指定其他型号。
```

#### 固件下载链接映射（已知型号）

| MCU | BOARD_NAME | 烧录方式 |
|-----|-----------|---------|
| ESP32 | ESP32_GENERIC | 串口烧录（device_command） |
| ESP32-S3 | ESP32_GENERIC_S3 | 串口烧录（device_command） |
| ESP32-C3 | ESP32_GENERIC_C3 | 串口烧录（device_command） |
| ESP32-S2 | ESP32_GENERIC_S2 | 串口烧录（device_command） |
| ESP32-C6 | ESP32_GENERIC_C6 | 串口烧录（device_command） |
| Pico | RPI_PICO | 按住 BOOTSEL 拖拽 .uf2 |
| Pico W | RPI_PICO_W | 同上 |
| Pico 2 | RPI_PICO2 | 同上 |
| Pico 2 W | RPI_PICO2_W | 同上 |
| ESP8266 | ESP8266_GENERIC | 串口烧录（device_command） |
| STM32F4DISC | STM32F4DISC | dfu-util |
| STM32F7DISC | STM32F7DISC | dfu-util |
| Pyboard | PYBV11 | dfu-util |
| Teensy 4.0 | TEENSY40 | Teensy Loader |
| Teensy 4.1 | TEENSY41 | Teensy Loader |

---

### Step 2: 引脚分配

#### Step 2A: 引脚事实来源（服务器提供，权威）

**绝不向用户索取引脚图，也绝不让用户确认引脚。** 引脚事实由服务器在系统提示中以
`--- PIN FACTS (server-provided; authoritative) ---` 区块注入，来自芯片级引脚事实表
（`content/chips/<chip>.json`）加板卡暴露引脚叠加：

- `usable_gpio`：每个可用 GPIO 的 `roles`（i2c/spi/uart/gpio_in/gpio_out/pwm/adc/dac…）与 `flags`（strapping/input_only/reserved_repl…）
- `default_buses`：I2C/SPI/UART 默认总线引脚
- `reserved_pins`：禁止使用（如 flash 6–11）
- `exposed_pins`：该板卡实际引出的引脚（值为 `all_chip_gpio` 时用整芯片 GPIO）
- `silkscreen_aliases`：丝印名 → GPIO

若 PIN FACTS 缺失或 `authoritative_pin_facts=false`：**不得猜测、不得索取引脚图** ——
按 `structured_errors`（code `chip_pin_facts_missing`）输出 `status=failed`。

#### Step 2B: 从 PIN FACTS 建立事实集（取代旧的“上传引脚图 + 多模态识图”）

直接从注入的 PIN FACTS 读取事实，不再依赖用户上传：
- 可用 GPIO 及其 `roles`/`flags`
- 硬件 I2C/SPI/UART 默认引脚（`default_buses`）
- 只读引脚（`flags` 含 `input_only`）
- strapping/boot 引脚（`flags` 含 `strapping`）
- flash/PSRAM 占用引脚（`reserved_pins`）
- REPL/USB 串口引脚（`flags` 含 `reserved_repl`）

#### Step 2C: 分配引脚

**LLM 按以下规则推理分配：**

```
规则 1 — I2C 器件：
  ├─ 所有 I2C 器件挂同一条 I2C 总线（默认 I2C0）
  ├─ 地址冲突 → 用第二组 I2C（如有） 或 Software I2C（任意 GPIO）
  └─ 每条 I2C 总线占 2 个 GPIO（SCL + SDA）

规则 2 — SPI 器件：
  ├─ 共享 MOSI/MISO/SCK，每个器件独立 CS
  ├─ 用硬件 SPI 默认引脚
  └─ N 个 SPI 器件占 3 + N 个 GPIO

规则 3 — UART 器件：
  ├─ 优先 UART1/UART2（UART0 被 REPL 占用）
  └─ 每个 UART 器件占 2 个 GPIO（TX + RX）

规则 4 — GPIO 简单器件（LED/蜂鸣器/按键/继电器）：
  ├─ 优先用远离 I2C/SPI 总线的引脚
  ├─ 避开启动敏感引脚
  ├─ 避开只读引脚
  └─ 每个器件占 1 个 GPIO

规则 5 — ADC 器件：
  ├─ 只能用 ADC 引脚（如 ESP32: GPIO32-39 中的 ADC1）
  └─ 注意 ESP32 ADC2 与 WiFi 冲突

规则 6 — 冲突检测：
  ├─ 同一 GPIO 不能被分配两次
  ├─ 打印分配后引脚占用表
  └─ 标注共享引脚（如 I2C 总线上的多个器件）
```

**分配输出格式：**

```
引脚分配方案：

  I2C 总线 (I2C0):
    SCL = GPIO22, SDA = GPIO21
    器件：SHT30 (0x44), SSD1306 (0x3C), BMP280 (0x76)
    地址无冲突 ✓

  GPIO 独立：
    蜂鸣器 = GPIO4
    LED    = GPIO13

  未使用默认引脚：SPI（无 SPI 器件）

  引脚占用：6/26 GPIO
  冲突检查：通过 ✓
```

**引脚电气类型 (type) 枚举映射：**

| 引脚用途 | type 值 |
|---------|---------|
| 3.3V 电源输出 | `power_3v3` |
| 5V 电源输出 | `power_5v` |
| GND | `gnd` |
| I2C SDA | `i2c_data` |
| I2C SCL | `i2c_clock` |
| SPI MOSI | `spi_mosi` |
| SPI MISO | `spi_miso` |
| SPI SCK | `spi_sck` |
| SPI CS | `spi_cs` |
| UART TX | `uart_tx` |
| UART RX | `uart_rx` |
| GPIO 输出 (LED/蜂鸣器/继电器) | `gpio_out` |
| GPIO 输入 (按键) | `gpio_in` |
| GPIO 输入+上拉 | `gpio_in_pullup` |
| ADC 输入 | `adc` |
| PWM 输出 | `pwm` |
| I2S BCK/WS/DIN/DOUT | `i2s_bck` / `i2s_ws` / `i2s_data_in` / `i2s_data_out` |

**物理引脚编号 (physical_pin) 获取规则：** `physical_pin` 为可选字段。
- 优先用 PIN FACTS 的 `silkscreen_aliases`（丝印名 → GPIO）标注对应关系
- 无 alias 数据时**省略** `physical_pin`（不得为此索取或让用户确认引脚图）

#### Step 2D: 电源引脚分配

**LLM 必须把电源引脚也写入 pinout：**

```
电源引脚分配：
  3V3(OUT) → 所有 I2C/SPI 器件的 VCC（传感器、屏幕等）
  5V(VBUS) → 需要 5V 的大功率器件（舵机、电机等）
  GND      → 所有器件的 GND（每个器件一根）

pinout 增加条目：
  {device: "电源", pin_name: "3V3(OUT)", gpio: "3V3", physical_pin: 36, type: "power_3v3", side: "right", pos: 16}
  {device: "电源", pin_name: "GND", gpio: "GND", physical_pin: 38, type: "gnd", side: "right", pos: 18}
```

---

#### Step 2D: 引脚安全分级与决策证据（domain 契约）

引脚事实源：板卡库有 board JSON 时以**完整 board JSON** 为 `firmware`/`pin_layout`/`restricted_gpio`/`onboard_peripherals` 的事实源；否则以用户确认的 pinout 图识别结果为准。`selected_board` 摘要不能替代完整事实。

**MCU 候选排序（未指定 MCU 时）**：候选池优先 Pico/RP2 + ESP32 系列；WiFi/BLE 加分 ESP32/Pico W，AI/语音/摄像头加分 ESP32-S3，低功耗加分 ESP32-C3，纯 GPIO/新手加分 Pico/Pico W。默认排序 Pico/Pico W → ESP32 DevKit → ESP32-S3 → ESP32-C3，输出 Top1 + Top2 备选。用户在 select-hw 要求**跨 MCU/芯片族/固件目标**换板 → 不出 success，输出 partial/checkpoint 回 analyze 重新确认。极致低价可加分 ESP8266/Pico，但 **ESP8266 不应压过 Pico/ESP32，除非预算是唯一主约束**。`cold-driver` 不影响 MCU 推荐、引脚分配或 BOM，只增加 warnings。

**引脚分配规则**：I2C 默认共享一条总线并优先 `default_bus_pins`，`i2c_addr` 冲突 → 改第二条或 partial；SPI 共享 MOSI/MISO/SCK、每器件独立 CS；UART 避开 REPL/USB；ADC 仅 ADC-capable 脚；GPIO 避开 boot/strapping、flash/PSRAM、USB OTG、只读脚；电源与 GND 必须进 `pinout`。用户接线优先保留但必须过 restricted/occupied 校验，**非法接线不得静默成功**；命中硬禁用脚/方向不符/被 `always_used` 板载外设占用 → 输出 `partial`、`checkpoint.resume_step=pin_assignment`、在 `structured_errors` 说明，**不自动换脚后继续 success**。

`restricted_gpio` 分级：

| board 字段 | 默认策略 | 校验级别 |
| --- | --- | --- |
| `flash_psram_occupied` | 禁止使用 | error |
| `reserved` / `internal_only` | 禁止使用 | error |
| `usb_serial_pins` | 默认禁止，除非明确不用 USB 串口或用户显式接线 | error/warning |
| `strapping` / `boot` | 默认避开；必须用时写 warning 记入 `notes`（无用户确认门） | warning（strict 为 error） |
| `input_only` | 只能用于输入类 pin | error |
| `adc_only` | 只能用于 ADC 输入 | error |
| `adc2_wifi_conflict` | 仅 `type=adc` 且 WiFi 启用时冲突；数字用途可用但须说明 | ADC=error，数字=warning |
| `onboard_peripherals[].occupied_pins` | `always_used=true` 禁止；否则避开或说明释放原因 | error/warning |

`pinout[].type` 枚举：`power_3v3` `power_5v` `gnd` `i2c_data` `i2c_clock` `spi_mosi` `spi_miso` `spi_sck` `spi_cs` `uart_tx` `uart_rx` `gpio_out` `gpio_in` `gpio_in_pullup` `adc` `pwm` `i2s_bck` `i2s_ws` `i2s_data_in` `i2s_data_out` `wifi_internal` `reserved`。

`pinout[]` 必填字段：`device` / `pin_name` / `gpio` / `type`（取上方枚举）；可选 `bus` / `i2c_addr` / `physical_pin` / `side` / `pos` / `notes`；建议 `source`（`default_bus`/`auto_assigned`/`user_wiring`/`onboard_peripheral`/`power`）。电源/地必须按真实 rail：`gpio` 为 `GND`/`3V3`/`5V` 时 `type` 必须为 `gnd`/`power_3v3`/`power_5v`，不得伪装成普通 GPIO。

**补充引脚分配规则（电气事实）**：

- **I2S**：需分配 BCK/WS/DIN/DOUT；麦克风与功放可共享 BCK/WS，但数据方向不同（一个 DIN、一个 DOUT）。
- 若 board JSON 有 `pin_options`，重映射只能在 `pin_options` 允许范围内；flexible matrix 也必须避开硬禁用脚。条件可用脚不作 schema 硬失败，交 warnings + 用户确认处理。
- 用板卡默认 UART/REPL/USB 串口脚做普通 GPIO 时，必须确认该串口不用于调试/通信，或写入 warning 并给出可重分配建议。
- 启用 WiFi 且用到 `adc2_wifi_conflict` 中的 GPIO 时，必须**完整列出所有相关 GPIO**；只有 `pinout[].type=adc` 才是冲突，作 I2C/I2S/数字用途允许，但须在 warnings/notes 说明“WiFi 只影响 ADC 读数，不影响数字用途”。

**结构化 `pin_decisions[]`（必须保留在 `manifest_content`，自然语言 notes 不能替代证据）**：每条含 `device` / `pin_name` / `assigned_gpio` / `decision_type` / `source` / `evidence` / `requires_user_review`，可选 `review_prompt` / `deviation`。

- `decision_type` 枚举：`use_default_bus` `auto_assign_free_gpio` `remap_default_conflict` `avoid_restricted_gpio` `avoid_onboard_occupied` `reuse_onboard_peripheral` `fixed_power_tie` `user_wiring` `manual_review_required`。
- `deviation`：`from_gpio` / `to_gpio` / `reason_code` / `evidence_path` / `evidence_value` / `validator_action`（`error`/`warning`/`manual_review`）。
- `reason_code` 枚举：`restricted_gpio` `default_bus_conflict` `onboard_occupied` `not_exposed` `user_requested` `fixed_power_tie` `insufficient_board_data`。`onboard_occupied` 的 `evidence_path` 必须指向 `onboard_peripherals[].occupied_pins` 且 `evidence_value` 与 `from_gpio` 一致，否则判 `pin_decision_invalid` 或转 `manual_review_required`。
- 配置/模式/使能/地址/增益/启动控制脚（`ADDR`/`BOOT`/`CFG`/`EN`/`GAIN`/`MODE`/`SEL` 等）固定接 `3V3/GND/5V` 时用 `decision_type=fixed_power_tie`、`source=fixed_power`，并给 `review_prompt`。

**审批安全门**：

- `approval_request`(`board_unavailable`)：用户指定板卡不在库/无 `pin_layout` 时，推荐同系列或功能相似且有 `pin_layout` 的已知板卡，允许改选或手动描述接线。
- **不使用 `pin_plan_review` 用户确认门**：自动分配基于服务器注入的权威 PIN FACTS，用户**不确认引脚**。条件可用脚、默认总线偏离、strapping 等风险只写入 `warnings`/`notes`，**不阻塞 success**。GPIO 汇总（`used_gpio` / `unused_gpio` / `restricted_or_occupied_gpio`）必须从 PIN FACTS 与最终 `pinout` 计算，不得手写静态列表。

**审批动作枚举与结构化接线（domain）**：

- `board_unavailable` 互斥动作：`use_recommended_similar`（用推荐的同系列/相似已知板卡）/ `select_known_board`（改选库内其他已知板卡，回 `board_select`）/ `manual_wiring_description`（用户手动描述接线 → partial/checkpoint，等结构化接线）/ `save_partial`。手动接线用数组表达，每条含 `mcu_pin` / `device` / `device_pin` / `signal` / `voltage` / `notes`。
- `pin_plan_review` 动作：`confirm_pin_plan`（按草案继续）/ `revise_pin_plan`（回 `pin_assignment` 重分配）/ `manual_wiring_description` / `save_partial`。
- 用户接线约束 `user_pin_constraints[]`：每条含 `device`（须对应 `devices[].name`/`pinout[].device`）/ `device_pin` / `mcu_pin`（`GPIO21` 与 `21` 视为同一脚；电源/地保持 `3V3`/`5V`/`GND`）/ `signal`（映射到 `pinout[].type`）/ 可选 `voltage` / `notes`。合法约束转成 `pinout[].source="user_wiring"` 并同步 `pin_decisions[]`（`decision_type="user_wiring"`）；**缺必填字段不得继续 success，输出 partial、`checkpoint.resume_step=pin_assignment`**；用户指定脚仍须过 board JSON 校验，非法脚不得静默改写。
- `hardware_plan.pin_review` **不再是 success 的必要条件**：自动分配无需用户确认引脚，**不得**因缺少 `pin_review` 或 `pin_review.confirmed` 而阻塞 success。风险记入 `warnings`/`notes`。

**结构化错误（`structured_errors[]`，写入 `manifest_content`）**：每条含 `code` / `severity` / `message`，可选 `evidence_path`。自由文本不能替代稳定 `code`——下游据 `code` 判定可否继续。

- `severity` 枚举：`info` / `warning` / `error` / `fatal`。
- `code` 建议枚举：`invalid_upstream_manifest` `missing_required_field` `invalid_enum` `board_not_found` `firmware_unknown` `missing_pin_layout` `pin_conflict` `i2c_address_conflict` `board_definition_not_found` `board_definition_invalid` `board_change_requires_analyze` `restricted_gpio_used` `default_bus_pin_deviation` `pin_review_required` `pin_review_rejected` `pin_decision_invalid` `onboard_peripheral_pin_used` `onboard_peripheral_reused` `user_wiring_invalid` `occupied_pin_conflict` `artifact_missing` `absolute_path_in_artifact` `permission_denied` `validate_failed` `timeout` `phase_complete_invalid`。

---

### Step 3: BOM 生成

```
物料清单：

  #  名称          型号              数量  单价    备注
  1  主控          {MCU型号}         1    ¥{xx}   含 USB 线
  2  {器件1}       {型号}           1    ¥{xx}   {接口}
  3  {器件2}       {型号}           1    ¥{xx}   {接口}
  -  面包板        830 孔            1    ¥8      可选
  -  杜邦线        公母各 20 根       1    ¥5
  -  USB 数据线    Micro-USB         1    ¥5      （若主控不含）

  预估总价：¥{total}

  vs 用户预算：{budget_yuan}
  {超预算/预算内}
```

价格来源：LLM 知识 + 常识估算。

---

### Step 4: 更新 manifest

用 `file_operation` 把硬件方案写入 `project-manifest.json`，**然后**用 `browser_validate` 的 `select_hw_manifest` / `manifest_phase` 校验（校验读取已写入的快照，务必先写后验）。

--- 写入字段：
- `phase`: "select-hw"
- `mcu`: {model, board, firmware_url, flash_tool}
  - `flash_tool` 取闭枚举：`serial`（ESP 系列串口/WebSerial）/ `uf2-drag-drop`（Pico/RP2）/ `dfu-util`（STM32/Pyboard）/ `teensy-loader`（Teensy）/ `unknown`
  - **固件版本只视为缓存（跨 skill 不变量）**：select-hw **不负责**确认 MicroPython 固件的实时最新版本；板卡库里的固件版本只能当缓存信息，正式烧录阶段（`upy-flash-mpy-firmware-browser`）才访问 `firmware.url` 检查最新 release。select-hw 输出重点保留 `firmware_url`、`firmware_board_name`、`flash_tool`，**不要把缓存版本当权威**——这与 flash skill 的“不信任缓存 `latest_version`”是同一不变量的上下游两半。
- `pinout`: [{device, pin_name, gpio, physical_pin, type, side, pos, notes}]
  - `physical_pin`: 物理引脚编号（如 Pico 的 GP4 = Pin 6）
  - `type`: 引脚电气类型枚举（见下方映射表）
  - `side`: 引脚在 MCU 哪一侧（left/right/top/bottom）
  - `pos`: 在 side 上的顺序位置（0-based）
- `bom`: [{name, model, quantity, unit_price_yuan, notes}]

---

## 与其他 skill 的关系

- ← `upy-analyze`：输入 manifest
- → `upy-scaffold`：传入完整硬件方案（mcu + pinout + bom）

## 强约束

- **MCU 只推荐 Pico 系列和 ESP32 系列**（除非用户指定其他型号）
- **固件核验是必须的**——确认有 MPY 固件再继续
- **引脚分配基于服务器注入的权威 PIN FACTS（芯片级引脚事实表 + 板卡暴露引脚）**——绝不索取、也绝不让用户确认引脚图；PIN FACTS 缺失即 fail-fast（`chip_pin_facts_missing`），绝不猜测
- **I2C 地址冲突必须检测**——不能把两个同地址器件放同一总线
- **启动敏感引脚必须避开**
