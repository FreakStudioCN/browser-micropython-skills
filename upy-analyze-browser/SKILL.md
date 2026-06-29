---
name: upy-analyze-browser
description: Phase 1 — analyze. Converts a one-sentence MicroPython hardware requirement into an analyze manifest inside Blockless Web Builder: intent parsing, device confirmation, driver search, alternative recommendation / cold-driver flagging. Triggers when the user describes "做一个 / 我想做 / 帮我写一个" a hardware project, or a project manifest is needed.
---

# upy-analyze-browser

## Purpose

Convert a one-sentence hardware requirement into an analyze manifest for `upy-select-hw-browser`: parse intent, generate and confirm the device list, search runtime/device drivers, and flag alternative recommendations or the cold-driver path. The analysis is performed by the LLM applying the rules below; `manifest_content` is the sole downstream handoff. Blockless Web Builder is the only target runtime for this browser skill.

## Plugin Equivalence

Equivalent source skills:
- `upy-analyze`
- `upy-analyze-plugin`

This browser contract preserves the source skill's responsibility, manifest schema, device-search rules, and failure semantics. Source-side script/protocol actions are replaced by Blockless primitives only:
- `file_operation`
- `approval_request`
- `browser_validate`
- `phase_complete`

Validation kinds retained for this phase:
- `manifest`
- `manifest_phase`
- `package_resolve`
- `awesome_micropython_search`

## Inputs

- Blockless project id, project store snapshot, and the user's one-sentence requirement.
- Driver-search results returned by the loaded Blockless package/network provider.
- Validation inputs for: `manifest`, `manifest_phase`, `package_resolve`, `awesome_micropython_search`.

## Outputs

- artifacts/analyze-manifest.json — the validated `manifest_content`.
- `phase_complete` for `analyze` with `status`, `evidence`, `artifacts`, `next_phase` (`upy-select-hw-browser`), and a recoverable `next_action` when needed.

## Blockless Primitive Sequence

1. `file_operation`: read the requirement and any prior project state.
2. Parse intent + build the device list (LLM-driven; see the domain/validate boundary section).
3. `browser_validate` (`package_resolve`, `awesome_micropython_search`): search drivers via the loaded provider (returns `partial` until loaded).
4. `approval_request`: confirm the device list with the user (the single main confirmation point).
5. `browser_validate` (`manifest`, `manifest_phase`): validate the manifest.
6. `file_operation` + `phase_complete`: persist the manifest and hand off to `upy-select-hw-browser`.

## Runtime State And Partial Results

- `phase_complete.status` is `success`, `partial`, or `failed`.
- `phase_complete.next_phase` is `upy-select-hw-browser` on success (with a valid `manifest_content`); `partial` sets `next_phase=null` with a checkpoint.
- Missing runtime state returns a partial envelope such as:

```json
{
  "status": "partial",
  "phase": "analyze",
  "capability_required": "browser_validate.package_resolve",
  "next_action": "load_provider"
}
```
- `capability_required` describes missing Blockless runtime state (e.g. the driver-search provider), not a browser limitation.

## Failure Conditions

- Return `failed` when the protocol/required fields are malformed, enums are illegal, or the manifest core structure is invalid.
- Return `partial` when the driver-search provider, project-store access, or user confirmation is missing.
- Include `capability_required` (`browser_validate.<kind>`) and `next_action` (`load_provider`/`sign_in`).
- Do not bypass Blockless primitives for local execution paths.

## Domain Analysis vs browser_validate (boundary)

Intent parsing, device confirmation, and driver search strategy are the LLM's job. `browser_validate` performs only the objective subset — manifest schema validation (`manifest`/`manifest_phase`) and provider-backed search (`package_resolve`/`awesome_micropython_search`). It does **not** decide the device list. Blockless Web Builder runs both.

## 职责

把用户的一句话硬件需求转换为可交给 `upy-select-hw` 的 analyze manifest。

只做：

- 解析需求和实现族。
- 生成并确认器件清单。
- 搜索内置运行时能力和具体器件驱动。
- 标记替代推荐或冷门驱动路径。
- 输出 `phase_complete`，其中 `payload.manifest_content` 是下游唯一主交接物。

不做：

- 不选 MCU 和板卡。
- 不分配引脚。
- 不生成业务代码。
- 不烧录设备。
- 不把插件端 UI 或设备日志解析逻辑写进插件。

## 运行模式

## 协议字段说明

先按本文件执行流程。本 browser skill 的执行面是 Blockless 原语：`file_operation`、`browser_validate`、`device_command`、`approval_request`、`phase_complete`；envelope、manifest、checkpoint、structured errors 和 artifacts 的字段含义与枚举见仓库 `contracts/` 下的 schema。

输出 JSON 时优先使用 `templates/*.json` 和 `mock-messages/analyze/*.json` 的形状，不要自由发挥字段名。

### 正式插件模式

插件通过 `start_phase` 启动：

```json
{
  "protocol_version": "1.0",
  "msg_id": "550e8400-e29b-41d4-a716-446655440000",
  "session_id": "4f6d9d72-9c4a-4f11-90df-3f2ad6e726cc",
  "phase": "analyze",
  "timestamp": "2026-06-21T00:00:00Z",
  "type": "start_phase",
  "payload": {
    "user_description": "做一个温湿度监测仪，超过阈值蜂鸣器报警",
    "pre_selected_board": null,
    "preferences": { "mode": "beginner", "locale": "zh" },
    "existing_hardware": []
  }
}
```

正式模式中：

- `session_id` 必须由插件创建并传入。
- skill/服务器必须继承同一个 `session_id`，不得另建正式 session。
- 所有 S->P 消息必须带完整 envelope。
- 本地文件、脚本、设备动作只能通过协议工具表达。

`start_phase` 字段速查：

| 字段 | 必填 | 来源 | 含义 |
|------|------|------|------|
| `protocol_version` | 是 | 插件 | 固定 `"1.0"` |
| `msg_id` | 是 | 插件 | 当前消息 UUID |
| `session_id` | 是 | 插件 | 当前工作流 session UUID，全流程保持不变 |
| `phase` | 是 | 插件 | 固定 `"analyze"` |
| `timestamp` | 是 | 插件 | ISO 8601 时间戳 |
| `type` | 是 | 插件 | 固定 `"start_phase"` |
| `payload.user_description` | 是 | 用户输入 | 一句话硬件需求 |
| `payload.pre_selected_board` | 否 | 插件 UI | 预选板卡；analyze 只记录，不核验 |
| `payload.preferences.mode` | 否 | 插件设置 | `beginner` 或 `custom`，默认 `beginner` |
| `payload.preferences.locale` | 否 | 插件设置 | 默认 `zh` |
| `payload.existing_hardware` | 否 | 用户资料 | 已有硬件数组，默认 `[]` |

### Claude Code 直测模式

没有真实插件宿主时，可以写调试产物，但这些文件不替代 `phase_complete.payload.manifest_content`。

如果输入缺少 `session_id`，直测模式必须生成 UUID，并强制使用 session 隔离目录：

```text
{test_root}/sessions/{session_id}/
  manifest_draft.json
  manifest_validated.json
  phase_complete.analyze.json
  driver_search_log.md
  analyze_phase_log.md
```

结束前必须通过 Blockless 校验（provider 未加载时返回 `partial`）：

- `browser_validate` (`manifest`)：校验 `manifest_draft`，得到 validated manifest
- `browser_validate` (`manifest_phase`)：用 validated manifest 校验 `phase_complete` envelope

任一校验失败，不得宣称 analyze 成功。

## V0 协议硬规则

### 完整 envelope

所有正式协议消息必须包含：

```json
{
  "protocol_version": "1.0",
  "msg_id": "uuid",
  "session_id": "uuid",
  "phase": "analyze",
  "timestamp": "2026-06-21T00:00:00Z",
  "type": "phase_complete",
  "payload": {}
}
```

要求：

- `protocol_version` 固定为 `"1.0"`。
- `msg_id` 使用 UUID 字符串。
- `session_id` 使用 UUID 字符串。
- 顶层 `phase` 和 `payload.phase` 都保留，且必须一致。

envelope 字段速查：

| 字段 | 必填 | 谁生成 | 规则 |
|------|------|--------|------|
| `protocol_version` | 是 | 发送方 | 固定 `"1.0"` |
| `msg_id` | 是 | 发送方 | 每条消息一个新 UUID |
| `session_id` | 是 | 插件 | 同一工作流不变 |
| `phase` | 是 | 发送方 | analyze 阶段固定 `"analyze"` |
| `timestamp` | 是 | 发送方 | ISO 8601，UTC 优先 |
| `type` | 是 | 发送方 | 消息类型 |
| `payload` | 是 | 发送方 | 类型专属对象 |

### result 枚举

`phase_complete.payload.result` 只允许：

| result | 含义 | next_phase | checkpoint |
|--------|------|------------|------------|
| `success` | analyze 完整成功，可进入下游 | `select-hw` | 不需要 |
| `partial` | 用户取消、中断、超时、缺输入或只完成部分搜索 | `null` | 必须有 |
| `failed` | 无法产生可用 manifest，或协议/格式校验失败 | `null` | 可选 |

`partial` 必须包含：

```json
{
  "checkpoint_id": "uuid",
  "resume_phase": "analyze",
  "resume_step": "driver_search",
  "resume_label": "继续 analyze 驱动搜索",
  "reason": "user_cancelled"
}
```

V0 只定义 checkpoint/resume 结构，不实现完整 resume runtime。

### errors 与 structured_errors

保留 `errors: string[]` 给人类阅读，同时输出 `structured_errors: object[]` 给插件 UI 和 orchestration：

```json
{
  "code": "manifest_validation_failed",
  "message": "devices[0].driver.source invalid",
  "severity": "error",
  "recoverable": true,
  "retryable": true,
  "source": "browser_validate.manifest"
}
```

`severity` 只允许 `info / warning / error / fatal`。

### artifact 统一模型

`artifacts` 必须是数组。调试文件路径使用 `file_list` artifact，不得写成对象映射。

`artifact.files[].status` 只允许：

```text
created / updated / unchanged / skipped / error
```

推荐 file item：

```json
{
  "path": "manifest_validated.json",
  "status": "created",
  "kind": "manifest",
  "mime_type": "application/json",
  "description": "校验规范化后的 analyze manifest"
}
```

`artifact_id` 不强制。`kind` 和 `description` 推荐填写；缺失时校验脚本可给 warning。

## 权限策略

采用“首次 session 弹一次总权限，后续沿用”的长流程策略。

analyze 阶段授权后允许：

- 写项目分析产物。
- 调用 `browser_validate`（`manifest` / `manifest_phase`）校验 manifest。
- 访问驱动搜索源，如 upypi、awesome-micropython、GitHub。

仍需单独确认的高风险动作：

- 删除文件。
- 烧录设备。
- 执行任意 shell。
- 上传或发布到 upypi。

## 取消、重试、超时

V0 先写进协议和 skill 说明，不实现完整 runtime：

- 用户取消 approval：输出 `result="partial"`，`next_phase=null`，写 checkpoint。
- 驱动搜索超时：优先降级为 warning；核心信息不可判断时才 failed。
- manifest 校验失败：允许修正后重试；重试沿用同一个 `session_id`。
- 重试行为记录在日志或 payload 元数据中。

## 执行步骤

### Step 1: 读取输入上下文

读取 `start_phase.payload`：

| 字段 | 必填 | 默认 | 说明 |
|------|------|------|------|
| `user_description` | 是 | 无 | 用户一句话需求 |
| `pre_selected_board` | 否 | `null` | 插件预选板卡，analyze 只记录，不核验 |
| `preferences.mode` | 否 | `beginner` | `beginner` 或 `custom` |
| `preferences.locale` | 否 | `zh` | 默认中文 |
| `existing_hardware` | 否 | `[]` | 用户已有硬件 |

如果字段缺失，按默认值补齐；如果 `user_description` 缺失或为空，输出 `phase_complete(result="failed")`，不得继续猜测需求。

发送：

```json
{
  "type": "status_update",
  "payload": {
    "level": "info",
    "message": "正在分析需求，先拆实现族和器件清单。",
    "step_id": "intent_extraction",
    "step_status": "running"
  }
}
```

### Step 2: 意图拆解和器件确认

从自然语言中提取：

- 项目名。
- 功能链路。
- 实现族。
- 器件清单。
- 接口类型。
- 用户指定器件 vs 系统推荐器件。

大类器件必须先拆实现族。例如土壤类必须区分 `ADC / RS485 Modbus / I2C/SPI / 组合方案`。

只保留一个必经确认点：`approval_request(device_confirm)`。

```json
{
  "type": "approval_request",
  "payload": {
    "approval_id": "device_confirm",
    "header": "确认项目方案",
    "question": "请确认器件方案；像土壤类器件，可在这里改成 ADC / RS485 Modbus / I2C 方案。",
    "summary": {
      "project_name": "温湿度监测报警器",
      "description": "定时采集温湿度，超过阈值蜂鸣器报警",
      "board": { "status": "none" }
    },
    "items": [],
    "allow_add": true,
    "allow_remove": true,
    "multi_select": true,
    "actions": [
      { "label": "确认，开始搜索驱动", "value": "confirm", "primary": true },
      { "label": "修改器件清单", "value": "modify" }
    ]
  }
}
```

`approval_request` 发出后必须等待用户响应，不得继续假装已确认。

### Step 3: 补充需求

`beginner` 默认补齐 requirements。`custom` 或信息明显不足时，最多发一张 `approval_request(requirement_supplement)`。

默认值：

| 字段 | 默认 |
|------|------|
| `scene` | `indoor` |
| `power` | `usb` |
| `network` | `none` |
| `sample_rate` | `normal_1hz` |
| `precision` | `normal` |
| `response_time` | `1s` |
| `temp_range` | `normal_0_40` |
| `size_constraint` | `none` |
| `budget_yuan` | `medium_50` |
| `experience` | `beginner` |
| `output` | `["serial"]` |
| `existing_hardware` | `[]` |
| `special_requirements` | `["none"]` |
| `mcu_specified` | `null` |

语音、云端、音频输出等 schema 不能完整表达的内容，记录在 `description`、`special_requirements`、device notes 和 warnings 中，不因 output 枚举不足直接失败。

### Step 4: 驱动搜索

对每个确认后的器件，分两层判断：

1. 底层运行时能力：
   - `machine.ADC`
   - `machine.Pin`
   - `machine.I2C`
   - `machine.SPI`
   - `machine.UART`
   - `machine.I2S`
   - `network`
   - `bluetooth`

2. 具体器件驱动：
   - `upypi`
   - `awesome-micropython`
   - `github`
   - 其他可信 MicroPython 来源

注意：

- `builtin_runtime` 只表示底层 API 可用，不等于具体 I2C/SPI/UART 器件驱动已找到。
- I2C/SPI/UART 具体器件仍应优先查 `upypi`。
- `micropython_lib` 只用于官方生态通用库/中间件，不作为普通传感器驱动默认来源。
- `driver.source="none"` 只在不是明显内置运行时能力，且所有驱动源都无结果时使用。

每个器件搜索过程发送 `status_update`。

系统推荐器件无驱动时，可推荐最多 2 个同类替代器件，使用 `approval_request(alternative_device)`。用户指定器件无驱动，或用户拒绝替代时，标记 `driver.source="cold-driver"`，由后续 `upy-gen-driver` 处理。

### Step 5: 构建 manifest_draft

生成 manifest 草稿，必须包含：

- `project_name`
- `requirements`
- `devices`

每个 device 必须包含：

- `name`
- `type`
- `interface`
- `source`: `user_specified` 或 `system_recommended`
- `quantity`
- `driver.source`

有效 `driver.source`：

```text
builtin_runtime / micropython_lib / upypi / awesome-micropython / github / local / cold-driver / none
```

**driver.source 分类硬规则（不可混为一谈）：**

先回答两层问题，不要把“固件已提供底层外设 API”和“已找到具体器件驱动包”混成同一结果：

- **`builtin_runtime`**：MicroPython 固件已提供底层运行时/外设 API（`machine.Pin`/`ADC`/`I2C`/`SPI`/`UART`/`I2S`、`network`、`bluetooth`、`neopixel`）。这类**不报“无驱动”**，标 `builtin_runtime` + `driver.module` + `notes`。但 `builtin_runtime` ≠ 已找到该具体器件现成驱动包——挂在 I2C/SPI/UART 上的具体器件仍要继续查 `upypi`。
- **`micropython_lib`**：官方生态通用库/中间件（如 `aioble`），区别于固件内置，也区别于普通 GitHub 第三方。**不是**具体器件驱动的默认首选源；若本质是器件驱动，优先 `upypi`。
- **具体器件驱动优先级**：`upypi` → `awesome-micropython` → `github` → 其他明确可验证的兼容来源。`source` 取这三者之一时必须来自 `upy-pkg-guide` 或等价 adapter 的**结构化结果**，不得由 LLM 字符串拼接或规则推断直接断言；mock/test 数据必须标记，不得伪装成真实查询。
- **硬约束**：不得把 Python `PyPI` 当 MicroPython 驱动主搜索入口；只发现普通 Python 包不算可用驱动；固件内置能力**不得**写成 `local`（`local` 只用于确实存在本地私有驱动资产）；依赖 `machine.*`/`network`/`bluetooth`/`neopixel` 却写成 `none` 视为 analyze 输出**错误**。
- **`none`** 仅用于：确实不是内置能力 **且** `upypi`/`awesome-micropython`/`github`/`micropython_lib` 均无可用驱动。
- “不是单一型号、而是一大类实现方案”的器件（如“土壤温湿度传感器”可拆为 ADC 电容式 / UART-RS485-Modbus 一体式 / I2C-SPI 数字式 / 组合方案），必须**先拆实现族再做驱动搜索**。

**最小 manifest 交付**：`manifest_content` 必须保留下游所需字段——`requirements.*`、设备字段、行为/notes、driver 包字段（`package_name`/`version`/`install_cmd`/`api_ref`/`repo_url`）；`api_ref` 优先结构化对象（`{"init":...,"read":...}`），来源仅一句摘要时先写 `notes`，不要伪装成完整 API。

### Step 6: 强制校验 manifest

必须调用 `browser_validate` (`manifest`) 校验 `manifest_draft`，得到 validated manifest（provider 未加载时返回 `partial`）。

校验失败：

- 修正草稿后可重试。
- 仍失败则输出 `phase_complete(result="failed")`。
- 不得继续输出 `success`。

### Step 7: 输出 phase_complete

成功时输出完整 envelope：

```json
{
  "protocol_version": "1.0",
  "msg_id": "550e8400-e29b-41d4-a716-446655440001",
  "session_id": "4f6d9d72-9c4a-4f11-90df-3f2ad6e726cc",
  "phase": "analyze",
  "timestamp": "2026-06-21T00:00:00Z",
  "type": "phase_complete",
  "payload": {
    "phase": "analyze",
    "result": "success",
    "summary": "器件分析完成，manifest 已通过校验。",
    "next_phase": "select-hw",
    "manifest_content": {},
    "artifacts": [
      {
        "type": "file_list",
        "title": "Claude Code 直测产物",
        "files": [
          {
            "path": "manifest_draft.json",
            "status": "created",
            "kind": "manifest_draft",
            "mime_type": "application/json",
            "description": "校验前 manifest 草稿"
          },
          {
            "path": "manifest_validated.json",
            "status": "created",
            "kind": "manifest",
            "mime_type": "application/json",
            "description": "校验规范化后的 analyze manifest"
          },
          {
            "path": "phase_complete.analyze.json",
            "status": "created",
            "kind": "phase_complete",
            "mime_type": "application/json",
            "description": "完整 analyze 阶段完成消息"
          },
          {
            "path": "driver_search_log.md",
            "status": "created",
            "kind": "log",
            "mime_type": "text/markdown",
            "description": "驱动搜索记录"
          }
        ]
      }
    ],
    "warnings": [],
    "errors": [],
    "structured_errors": []
  }
}
```

`phase_complete.payload` 字段速查：

| 字段 | 必填 | success | partial | failed |
|------|------|---------|---------|--------|
| `phase` | 是 | `"analyze"` | `"analyze"` | `"analyze"` |
| `result` | 是 | `"success"` | `"partial"` | `"failed"` |
| `summary` | 是 | 成功摘要 | 中断摘要 | 失败摘要 |
| `next_phase` | 是 | `"select-hw"` | `null` | `null` |
| `manifest_content` | 是 | 校验后的 manifest | 当前最佳 manifest 快照 | 尽量给出当前快照 |
| `checkpoint` | 条件 | 不需要 | 必须 | 可选 |
| `artifacts` | 是 | 数组 | 数组 | 数组 |
| `warnings` | 是 | 字符串数组 | 字符串数组 | 字符串数组 |
| `errors` | 是 | 空数组或错误摘要 | 空数组或错误摘要 | 错误摘要 |
| `structured_errors` | 是 | 空数组 | 可选结构化错误 | 必须描述主要失败 |

直测模式建议额外写 `analyze_phase_log.md`，但它不是正式协议必交产物；可以在 `file_list` 中声明。

产出 `phase_complete` envelope（直测模式可写 `phase_complete.analyze.json`）后必须调用 `browser_validate` (`manifest_phase`)，用 validated manifest 校验该 envelope。

校验失败不得宣称完成。

## 交付文件

正式插件模式以消息为准。Claude Code 直测模式在 session 目录下写：

- `manifest_draft.json`
- `manifest_validated.json`
- `phase_complete.analyze.json`
- `driver_search_log.md`
- `analyze_phase_log.md`（建议）

## 模板和 mock

使用本 skill 自带资源：

- `templates/envelope.phase_complete.json`
- `templates/checkpoint.json`
- `templates/structured_error.json`
- `templates/artifact.file_list.json`
- `mock-messages/analyze/*.json`
- `references/v0-protocol.md`

修改模板、枚举或输出格式后，必须更新校验脚本和 smoke 测试。

## 强约束

- 协议格式、必填字段、枚举非法、manifest 核心结构错误必须作为 error。
- 业务语义问题优先 warning，例如 TouchPad 板卡兼容性、语音 output schema 不完整。
- `phase_complete.payload.manifest_content` 是下游唯一主交接物。
- `manifest_validated.json` 与 `phase_complete.payload.manifest_content` 必须核心字段一致，时间字段不参与严格比较。
- `phase_complete.artifacts` 必须是数组。
- `errors` 必须是字符串数组，`structured_errors` 必须是对象数组。
- `partial` 必须 `next_phase=null` 且有 checkpoint。
- `success` 必须 `next_phase="select-hw"` 且有合法 `manifest_content`。

