---
name: upy-scaffold-browser
description: Phase 3 — project skeleton generation inside Blockless Web Builder. Reads the select-hw manifest and generates the complete firmware/ skeleton per the scheduling mode (Timer/asyncio/_thread). Triggers after upy-flash-mpy-firmware-browser.
---

# upy-scaffold-browser

## Purpose

From the select-hw manifest, determine the scheduling mode and generate the complete `firmware/` project skeleton. Writes no business logic, fills no driver code, performs no async-driver conversion. The skeleton is produced by the LLM applying the rules below; `browser_validate` validates the result. Blockless Web Builder is the only target runtime for this browser skill.

## Plugin Equivalence

Equivalent source skills:
- `upy-scaffold`
- `upy-scaffold-plugin`

This browser contract preserves the source skill's responsibility, scheduling-mode templates, directory layout, and failure semantics. Source-side local file writes and lint validation are replaced by Blockless primitives only:
- `file_operation`
- `approval_request`
- `browser_validate`
- `phase_complete`

Validation kinds retained for this phase:
- `scaffold_generate`
- `scaffold_contract`
- `python_syntax`
- `project_files`

## Inputs

- Blockless project id, project store snapshot, and the select-hw `manifest_content`.
- Validation inputs for: `scaffold_generate`, `scaffold_contract`, `python_syntax`, `project_files`.

## Outputs

- The complete `firmware/` skeleton (board.py, conf.py, boot.py, main.py stub, drivers/, tasks/, lib/, tools/) in the project store.
- `phase_complete` for `scaffold` with `status`, `evidence`, `artifacts`, `next_phase` (`upy-generate-browser`), and a recoverable `next_action` when needed.

## Blockless Primitive Sequence

1. `file_operation`: read the select-hw manifest.
2. `approval_request`: confirm the scheduling mode (Timer/asyncio/_thread) and optional modules.
3. Generate the skeleton per the rules below (LLM-driven; see the domain/validate boundary section).
4. `file_operation`: write the `firmware/` skeleton to the project store.
5. `browser_validate` (`scaffold_generate`, `scaffold_contract`, `python_syntax`): validate the skeleton.
6. `phase_complete`: hand off to `upy-generate-browser`.

## Runtime State And Partial Results

- `phase_complete.status` is `success`, `partial`, or `failed`.
- `phase_complete.next_phase` is `upy-generate-browser` on success.
- Missing runtime state returns a partial envelope such as:

```json
{
  "status": "partial",
  "phase": "scaffold",
  "capability_required": "browser_validate.scaffold_contract",
  "next_action": "load_provider"
}
```
- `capability_required` describes missing Blockless runtime state or provider registration, not a browser limitation.

## Failure Conditions

- Return `failed` when the input manifest is malformed or the generated skeleton fails contract/syntax validation.
- Return `partial` when a required Blockless provider, project-store access, or user approval is missing.
- Include `capability_required` (`browser_validate.<kind>`) and `next_action` (`load_provider`/`sign_in`).
- Do not bypass Blockless primitives for local execution paths.

## Domain Generation vs browser_validate (boundary)

Choosing the scheduling mode and generating the skeleton is the LLM's job. `browser_validate` performs only the objective subset — skeleton contract + syntax (`scaffold_generate`/`scaffold_contract`/`python_syntax`). It does **not** decide the skeleton shape. Blockless Web Builder runs both.

## 角色定位

给定 `project-manifest.json`（phase: select-hw），确定调度模式，生成完整的 `firmware/` 项目骨架。**不写业务逻辑，不填充驱动代码，不转换异步驱动。**

---

## 前置检查

无需本地环境：脚手架生成与校验都通过 Blockless 原语完成（`file_operation` 写骨架，`browser_validate` 的 `python_syntax` / `scaffold_contract` 做客观校验）。

---

## 执行步骤

### Step 1: 审批选型 — 调度模式 + 额外文件

读取 `project-manifest.json`，使用 **AskUserQuestion** 呈现多选审批界面。

#### 1A: 调度模式（单选，推荐标记）

```
推荐规则（仅用于标记 Recommended，不影响可选项）：
  devices 中有 display 且含 LVGL              → async
  requirements.network = wifi                 → async
  requirements.special_requirements 含 "lcd"  → async
  默认                                        → timer
```

AskUserQuestion：

```
header: "调度模式"
question: "选择调度模式（推荐项已标注）："
options:
  - Timer tick (Recommended) — ISR 计数 + 主循环轮询，适合纯传感器采集
  - asyncio — uasyncio 原生协程，适合 WiFi / LVGL / LCD
  - _thread — 多线程，适合阻塞式操作
```

_mode 仅用于骨架生成时的 main.py 和 task stub 形态选择，驱动转换（同步→异步）由 `upy-generate` 负责。_

#### 1B: 额外模块（多选）

```
header: "额外模块"
question: "是否需要注入以下可选模块？（可多选）"
multiSelect: true
options:
  - 日志系统 (lib/logger/*) — logging + rotating_logger，设备端日志记录与轮转
  - 性能计时器 (lib/time_helper.py) — timed_function / timed_coro 装饰器，统计函数耗时
  - 维护任务 (tasks/maintenance.py) — GC 检查 + 空闲回调
  - 部署工具 (tools/flash_device.py) — mpy 编译 + 固件烧录 + 文件上传
  - PC 日志读取 (tools/read_device_log.py + log_report.py) — 从 PC 读取设备日志并生成 JSON 报告
```

#### 1C: 用户自定义文件（多选 + 自由输入）

```
header: "自定义"
question: "是否需要额外生成自定义文件？"
options:
  - 不需要额外文件
  - 自定义目录/文件（请在 Other 中输入，如 firmware/lib/my_utils.py, host/gui.py）
```

---

#### Step 1 的结构化配置契约

`approval_request`(`scaffold_config`) 用 `item_groups` 表达两组选择：

| group | 选择性 | 选项 id |
|-------|--------|---------|
| `scheduler_mode` | 单选 | `mode_timer` / `mode_async` / `mode_thread` |
| `extra_modules` | 多选 | `module_logger` / `module_time_helper` / `module_maintenance` / `module_flash` / `module_log_tools` |

**调度模式推荐规则**（只影响默认 `selected/meta`，不限制用户选择）：`requirements.network == "wifi"` → `mode_async`；器件或 `special_requirements` 含 lcd/lvgl/display → `mode_async`；其他 → `mode_timer`。

**模块 id → 输出映射**：

| id | 输出 |
|----|------|
| `module_logger` | `firmware/lib/logger/*` |
| `module_time_helper` | `firmware/lib/time_helper.py` |
| `module_maintenance` | `firmware/tasks/maintenance.py` |
| `module_flash` | `tools/flash_device.py` |
| `module_log_tools` | `tools/read_device_log.py` + `tools/log_report.py` |

**非法组合**：未选 `module_maintenance` → `main.py` 不得 import 或调用 `maintenance_tick`；模式非 `timer` → 不得注入 `firmware/lib/scheduler/timer_sched.py`。

### Step 2: 按模式处理

#### 模式 A: Timer tick（默认）

**不额外获取外部文档**。注入 `lib/scheduler/timer_sched.py`，ISR 计数 + 主循环轮询。

#### 模式 B: asyncio

**WebFetch MicroPython asyncio 官方文档**以确认 API 用法：

```
WebFetch: https://docs.micropython.org/en/latest/library/asyncio.html
提取：create_task, run, sleep_ms, gather, Event, Queue 等 API
```

**不注入 scheduler.py**。main.py 直接使用 `uasyncio` 原生 API。

#### 模式 C: _thread

**WebFetch Python _thread 官方文档**以确认 API 用法：

```
WebFetch: https://docs.python.org/3.5/library/_thread.html#module-_thread
提取：start_new_thread, allocate_lock, exit 等 API
```

**不注入 scheduler.py**。main.py 直接使用 `_thread` 原生 API。

---

### Step 3: 生成项目骨架

用 `browser_validate` 的 `scaffold_generate` 按调度模式（timer/async/thread）生成骨架，用 `file_operation` 写入项目存储：

**脚本自动完成：**

| 步骤 | 文件 | 方式 |
|------|------|------|
| board.py | pinout → BOARDS 字典 + 查询函数 | 生成 |
| conf.py | requirements → 采样率/日志/看门狗常量 | 生成 |
| boot.py | WDT + emergency_exception_buf | 生成 |
| main.py | 按模式生成不同入口 | 生成 |
| lib/logger/* | logging + rotating_logger + __init__ | 复制模板 |
| lib/time_helper.py | timed_function + timed_coro | 复制模板 |
| lib/scheduler/* | timer_sched.py + __init__ | **仅 timer 模式** |
| tasks/maintenance.py | GC 检查 + 错误回调 | 复制模板 |
| drivers/* | 每个器件一个 stub 包 | 生成 |
| tools/flash_device.py | .py→.mpy 编译 + 烧录 + 上传 | 复制模板 |
| tools/read_device_log.py | PC 端设备日志读取 | 复制模板 |
| tools/log_report.py | 日志→JSON 报告解析 | 复制模板 |
| host/ | PC 上位机代码（不做约束） | .gitkeep |
| test/device/ | 设备端 unittest 测试框架 | .gitkeep |
| test/pc/ | PC 端测试脚本 | .gitkeep |
| build/firmware/ | .bin/.uf2/.hex 固件 | .gitkeep |
| build/mpy/ | 编译后 .mpy 文件 | .gitkeep |
| firmware/assets/ | 设备端资源文件（音频等） | .gitkeep |
| docs/ | 项目文档入口 | .gitkeep（必须保留） |
| README.md | 项目名 + BOM + 引脚表 | 生成 |
| LICENSE | MIT | 生成 |
| — | 客观校验 | `browser_validate` 的 `python_syntax` / `scaffold_contract` 自动执行 |

---

### 三种模式的 main.py 形态

main.py 由 scaffold **仅生成硬件实例化 + 调度器框架**，task 注册留给 `upy-generate`。

**Timer：**
```python
from machine import Pin, I2C
from lib.scheduler.timer_sched import Scheduler
from tasks.maintenance import maintenance_tick

# Pin numbers from manifest.hardware.pinout
i2c = I2C(<bus_id>, scl=Pin(<scl>), sda=Pin(<sda>), freq=400000)
# ...

sc = Scheduler(timer_id=<port_timer_id>, tick_ms=100, idle_cb=maintenance_tick)
# TODO: upy-generate registers tasks here
sc.start()
```

`<port_timer_id>` 必须按 MicroPython port 选择：只有 RP2/Pico/RP2040/RP2350 和 Zephyr 使用 `-1` virtual Timer；其他 MCU/port 默认使用 `0` 或其他已验证非负硬件 Timer ID。

**asyncio：**
```python
import uasyncio as asyncio
from machine import Pin, I2C
from tasks.maintenance import maintenance_tick

i2c = I2C(<bus_id>, scl=Pin(<scl>), sda=Pin(<sda>), freq=400000)
# ...

async def main():
    # TODO: upy-generate creates async tasks here
    while True:
        maintenance_tick()
        await asyncio.sleep_ms(100)
asyncio.run(main())
```

**_thread：**
```python
import _thread
import time
from machine import Pin, I2C
from tasks.maintenance import maintenance_tick

i2c = I2C(<bus_id>, scl=Pin(<scl>), sda=Pin(<sda>), freq=400000)
# ...

# TODO: upy-generate starts threads here
while True:
    maintenance_tick()
    time.sleep_ms(100)
```

---

## 与其他 skill 的关系

- ← `upy-select-hw`：输入 manifest（mcu + pinout + bom + devices）
- → `upy-generate`：传入完整骨架 + manifest，业务代码生成
- → `upy-wiring`：引脚分配表 → 接线图
- → `upy-diagram`：代码结构 → 架构图
- → `upy-simulate`：PC 端全流程业务模拟

---

## 强约束

- **不生成业务 task 文件**：`tasks/` 下只放通用工具（`maintenance.py` + `__init__.py`），业务 task（sensor/display/alarm/network）由 `upy-generate` 创建
- **不转换驱动**：驱动同步/异步转换是 `upy-generate` 的职责
- **asyncio / _thread 模式不注入 scheduler.py**：直接用原生 API，不额外封装
- **timer 模式使用已有 Scheduler.py 参考实现**：ISR 只计数，主循环执行
- **board.py 不做硬件初始化**：只存常量映射，实例创建在 main.py
- **conf.py 不放敏感数据**：无 Wi-Fi 密码、API Key
- **生成结束自动 `browser_validate` 校验**：`python_syntax` / `scaffold_contract` 自动验证，不通过打印 warning
- **`Scheduler` 端口规则（timer 模式）**：保留内部库默认 `timer_id=-1`（RP2/Pico、Zephyr 只支持虚拟 Timer）；端口差异在 `main.py` 装配层解决——仅 RP2/Pico/RP2040/RP2350、Zephyr 显式生成 `Scheduler(timer_id=-1, tick_ms=...)`，其他 MCU 生成 `Scheduler(timer_id=0, ...)` 或已验证的非负硬件 Timer ID，不得生成隐式 `Scheduler(...)`/`Scheduler(tick_ms=...)`
- **GPIO 方向来自 `pinout[].type`**：`gpio_out`/`DATA`/`DO`/`OUT`/`GAIN`/`SD` 默认 `Pin.OUT`，`gpio_in` 默认 `Pin.IN`——不要把 WS2812 DATA 这类输出脚生成成 `Pin.IN`
- **`main.py` 启动期 fatal guard**：装 rotating logger 后关键启动状态 `print + logger` 双写；未捕获的启动/装配异常必须 `sys.print_exception()` 打串口 + `logger.exception()` 写 `/log/run_*.log`，不依赖 MPY 自动落盘
- **生产部署过滤规则（写入 manifest 供 deploy 消费）**：`main.py`/`boot.py`/`conf.py` 始终以 `.py` 部署不编译；`drivers/**/mock.py` 是测试替身不得编译/上传，stale `mock.mpy` 也跳过——deploy 的 `deploy_plan` 据此判定禁止产物
- **不伪造工具/schema**：写入骨架的 schema 与工具脚本只能是当前仓库真实存在的，不要伪造不存在的后续工具或 schema
- **最终交付契约**：`project-manifest.json` 经 `file_operation` 写入项目根；`phase_complete.artifacts` 至少含 `file_tree` 与 `file_list`；success 时 `next_phase=upy-generate-browser`，partial/failed 时 `next_phase=null`
