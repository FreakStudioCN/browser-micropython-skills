---
name: upy-generate-browser
description: Phase 4 — business code generation. Reads the scaffold-phase manifest, resolves drivers, and generates DI-architecture business code, a Mock layer, and unit tests inside Blockless Web Builder. Runs after upy-scaffold-browser completes.
---

# upy-generate-browser

## Purpose

Generate and validate MicroPython firmware business code from the selected hardware manifest: resolve drivers, read their source as the Mock authority, generate the DI factory + Mock + task code + conf.py + main.py + tests, and run objective validation. Code understanding and generation are performed by the LLM applying the rules in this skill. Blockless Web Builder is the only target runtime for this browser skill.

## Plugin Equivalence

Equivalent source skills:
- `upy-generate`
- `upy-generate-plugin`

This browser contract preserves the source skill's phase responsibility, generation rules, required evidence, artifacts, and failure semantics. Source-side file, validation, package, and lint actions are replaced by Blockless primitives only:
- `approval_request`
- `file_operation`
- `browser_validate`
- `phase_complete`

Validation kinds retained for this phase:
- `generate_quality`
- `python_syntax`
- `package_resolve`
- `upypi_resolve`
- `mpy_compile`

## Inputs

- Blockless project id, project store snapshot, and the scaffold-phase manifest (`phase: scaffold`).
- The scaffold skeleton (`firmware/` tree) and any prior phase artifacts.
- Driver package names to resolve, plus the resolved driver source/README/example returned by the Blockless package provider.
- Validation inputs for: `generate_quality`, `python_syntax`, `package_resolve`, `upypi_resolve`, `mpy_compile`.

## Outputs

- Generated firmware files written to the Blockless project store: `firmware/lib/`, `firmware/drivers/*/__init__.py` (factory) + `mock.py`, task files, `conf.py`, `main.py`, and `test/` files.
- artifacts/generate-quality.json
- `phase_complete` for `generate` with `status`, `evidence`, `artifacts`, `next_phase` (`upy-deploy-browser`), and a recoverable `next_action` when needed.

## Blockless Primitive Sequence

1. `file_operation`: read the scaffold manifest, the `firmware/` skeleton, and prior artifacts.
2. `browser_validate` (`package_resolve`, `upypi_resolve`): resolve each driver package; the loaded Blockless package provider returns the driver `.py`, README, and example contents (returns `partial` until a provider is loaded).
3. Apply the generation rules below (LLM-driven; see the domain/validate boundary section): factory + Mock + tasks + conf.py + main.py + tests.
4. `file_operation`: write generated files to the project store.
5. `browser_validate` (`python_syntax`, `generate_quality`, `mpy_compile`): objective validation of the generated files.
6. `approval_request`: confirm any driver-source modification (DI injection / line-ending fix) before overwriting a downloaded driver.
7. `phase_complete`: return status, evidence, artifacts, and `next_phase: upy-deploy-browser`.

## Runtime State And Partial Results

- `phase_complete.status` is `success`, `partial`, or `failed`.
- `phase_complete.evidence` names validation results, generated file artifacts, and user approvals used by the phase.
- `phase_complete.next_phase` is `upy-deploy-browser` when the phase succeeds.
- Missing runtime state returns a partial envelope such as:

```json
{
  "status": "partial",
  "phase": "generate",
  "capability_required": "browser_validate.package_resolve",
  "next_action": "load_provider"
}
```
- `capability_required` describes missing Blockless runtime state or provider registration, not a browser limitation.

## Failure Conditions

- Return `failed` when required input is malformed, generated project files are invalid, or validation evidence reports blocking errors.
- Return `partial` when a required Blockless provider (package/network/compile), project-store access, or user approval is missing.
- Include `capability_required` with the missing primitive path, for example `browser_validate.<kind>` or `file_operation.<action>`.
- Include `next_action` as `load_provider`, `sign_in`, or `grant_file_access` for recoverable runtime gaps.
- Do not bypass Blockless primitives for local execution paths.

## Domain Generation vs browser_validate (boundary)

Code understanding and generation are performed by the LLM applying the rules below. `browser_validate` performs only the objective, decidable subset — does it parse (`python_syntax`), are required files present and non-empty (`generate_quality`), does it cross-compile (`mpy_compile`). Style conventions (line length ≤ 120, no unused imports, English strings) and all architectural rules are applied by the LLM; a validation pass does **not** replace them. Blockless Web Builder runs both.

## 核心哲学：以单元测试为核心的嵌入式开发

本项目生成的代码遵循 **以单元测试为核心的嵌入式开发** 方法论：

- **硬件与软件解耦**：除 `main.py`（DI 装配入口）外，所有代码文件不 `import machine`。驱动通过工厂函数注入，任务函数通过参数接收驱动对象。
- **依赖注入与模拟（Mock）**：真实驱动与 Mock 实现同一鸭子类型接口，task 函数不关心传入的是真实硬件还是模拟对象。PC 端可直接 `import` Mock 运行测试，无需任何硬件。
- **可测试性驱动设计**：每个 task 函数是纯 Python 函数，给定输入 → 产生输出，无全局状态。传感器报错、缺失（None）、正常数据三种情况均在 PC 端覆盖。
- **上位机 PC 端可模拟全部业务逻辑**：`test/pc/` 目录下的单元测试运行在 CPython，不依赖 MicroPython 运行时。lib/ 下的基础库（logger、time_helper 等）提供 CPython fallback 以支持此能力。

## 角色定位

给定 `project-manifest.json`（phase: scaffold），完成驱动解析、任务代码生成、DI 装配、测试生成。**代码理解和生成由 LLM 直接完成，不再依赖正则脚本。** 在 Blockless Web Builder 中，外部资源获取与校验都通过 Blockless 原语完成，无本地命令。

## Phase 1: 解析并获取驱动

通过 `browser_validate` 的 `package_resolve` / `upypi_resolve` 解析 manifest 中每个驱动包；已加载的 Blockless 包提供方返回驱动 `.py`、README、示例内容（provider 未加载时返回 `partial`），用 `file_operation` 写入 `firmware/lib/`：

| 文件 | 命名 | 用途 |
|------|------|------|
| 驱动 .py | `lib/<driver>.py` | 驱动源码，理解 API |
| README.md | `lib/<name>_README.md` | 接线图、API 说明、使用流程 |
| code/main.py（示例） | `lib/<name>_example.py` | 可运行示例，展示真实调用模式 |

### 1A: 换行符修复

包提供方返回的源文件可能包含 `\r\r\n` 等非标准换行符，会导致解析失败。写入后对 `lib/*.py` 跑 `browser_validate` `python_syntax`；若解析失败，由 LLM 规范化换行符（`\r\n`/`\r` → `\n`，移除续行反斜杠之间的空行）后用 `file_operation` 重写，并经 `approval_request` 确认对下载驱动的修改。

## Phase 2: LLM 理解驱动 → 生成工厂 + Mock

**对 manifest.devices 中的每个 device，逐一执行：**

### 2A: 阅读理解（Mock API 的唯一来源）

**Mock 的方法签名、参数、返回值类型必须从 `firmware/lib/` 的驱动源码中直接提取 —— 不依赖任何外部的 api_ref 字符串或预置数据库。**

用 `file_operation` 读取以下文件（如果存在）：
```
firmware/lib/<driver>.py          ← 驱动源码（Mock API 的权威来源）
firmware/lib/<name>_README.md     ← 使用文档
firmware/lib/<name>_example.py    ← 示例代码
```

从源码中理解：
- **主驱动类是哪个**：如果有多个类（如 `SSD1306` 基类 + `SSD1306_I2C` 子类），选 I2C/SPI 子类；没有子类则选第一个非 Exception 类
- **__init__ 参数**：区分 I2C 地址、Pin 脚号、配置参数
- **公开方法（Mock 覆盖目标）**：所有不以 `_` 开头的方法，逐一记录方法签名（参数名、默认值）和返回值类型。这些将直接决定 Mock 类的方法列表和默认返回值
- **是否是自建 I2C 的驱动**：`self.i2c = I2C(...)` → 需要修改驱动以支持外部传入 i2c

example.py 可以告诉你真实的调用方式：
```python
# 从 example 知道：BMP280(i2c=i2c, address=addr)、read_compensated_data() 返回 (temp, press, hum)
```

### 2B: 修改自建 I2C 的驱动（如果需要）

如果驱动在 `__init__` 中自己创建 I2C（如 SHT30 的 `self.i2c = I2C(scl=Pin(...), sda=Pin(...))`），用 `file_operation` 修改 `lib/<driver>.py`（修改前经 `approval_request` 确认）：

1. `def __init__(self, ...)` 末尾加 `, i2c=None`
2. 把 `self.i2c = I2C(...)` 包在 `if i2c is not None: self.i2c = i2c else: ...` 里
3. `self.i2c_addr` 等后续赋值留在 if/else 外面（两种分支都需要）

### 2C: 生成工厂函数 → `drivers/<name>_driver/__init__.py`

工厂文件是 DI 链条的第一环，导出 `create_<name>` 和 `scan_<name>_i2c` 两个函数，行为必须一致可靠。

**参考来源**：下载的 `lib/<name>_example.py`（即驱动包的 `code/main.py`）展示了真实的 I2C 地址、通信速率配置和调用方式，LLM 必须阅读该文件后再生成工厂代码。

```python
# -*- coding: utf-8 -*-
# @Generated : upy-generate
# @File    : drivers/<name>_driver/__init__.py
# @License : MIT

try:
    from lib.<module> import <DriverClass>
except ImportError:
    <DriverClass> = None

# Default I2C address from driver source / example.py
_<NAME>_DEFAULT_ADDR = <default_addr>


def create_<name>(i2c, address=None):
    """Create <DriverClass> instance. Returns driver object or None on failure."""
    if i2c is None:
        return None
    try:
        obj = <DriverClass>(i2c=i2c, address=address if address is not None else _<NAME>_DEFAULT_ADDR)
        return obj
    except Exception as e:
        from lib.logger import warning
        warning('Driver <NAME> init failed: {}'.format(e))
        print('[DRIVER] <NAME> init failed:', e)
        return None


def scan_<name>_i2c(i2c, address=None):
    """Scan I2C bus for <NAME>. Returns True if device found at address.

    Does NOT create a driver instance — only checks if the I2C address
    responds on the bus. Used by upy-deploy-browser for hardware connectivity check.

    NOTE: Some sensors (e.g. GT911) have software-configurable addresses
    that cannot be detected via passive scan. For these, consult the
    downloaded example.py — scan may return False until the device is
    initialized, or require a different detection strategy.
    """
    if i2c is None:
        return False
    addr = address if address is not None else _<NAME>_DEFAULT_ADDR
    return addr in i2c.scan()
```

- I2C 器件：工厂接受 `i2c, address=None`，扫描函数独立于驱动实例
- GPIO 器件（buzzer/led，source=none）：工厂接受 `pin_num`，内部创建 `Pin(pin_num, Pin.OUT)`。**GPIO 器件没有现成驱动，需要 LLM 从头写合理的封装**（on/off/toggle/value），Mock 同样覆盖这些方法。GPIO 器件不需要 scan 函数
- SPI 器件：工厂接受 `spi, cs_pin`，内部创建 `Pin(cs_pin, Pin.OUT)`
- 自建 I2C 驱动改过后：同样接受 `i2c, address=None`

### 2D: 生成 Mock → `drivers/<name>_driver/mock.py`

Mock 的方法列表和签名**直接从 Phase 2A 阅读驱动源码的结果中提取**，覆盖驱动所有公开方法，默认返回值与驱动返回类型匹配：

```python
# -*- coding: utf-8 -*-
# @Generated : upy-generate
# @File    : drivers/<name>_driver/mock.py
# @License : MIT

class Mock<Name>:
    """Mock <NAME> — same API as real driver, returns canned data."""

    def __init__(self, **kwargs):
        self._<method1> = kwargs.get('<method1>', <default>)
        ...

    def <method1>(self):
        return self._<method1>
    ...
```

默认值规则：
- 返回数值 → `0`
- 返回布尔 → `True`
- 返回元组 → `(<典型值>)`，如 `(25.0, 60.0)`
- 返回 None → 不存 `self._xxx`，方法体直接 `pass`

### 2E: async 模式特殊处理

如果 `manifest.scaffold_mode` 为 `async`：

**默认规则**：驱动本身不改（保持同步，async 化在封装层完成），工厂函数返回同步驱动对象不变。task 函数形态和 main.py 入口由 scaffold 骨架阶段决定，generate 阶段沿用。

**例外 —— 驱动中存在阻塞式方法时必须修改驱动源码**：

1. **I2S 外设等硬件阻塞操作**：查阅 MicroPython asyncio 官方文档确认是否有异步替代 API。若有（如 `I2S.readinto()` 的异步版本），在工厂封装层包装；若没有，需在驱动中增加非阻塞轮询路径。
2. **`time.sleep()` / `time.sleep_ms()` 等延时**：驱动中如果有延时等待（如传感器上电稳定等待、复位后延时），必须修改：
   - 将 `time.sleep(n)` 替换为 `await asyncio.sleep(n)` 或 `await asyncio.sleep_ms(n)`
   - 对应方法签名改为 `async def`
   - 参考文档：https://docs.micropython.org/en/latest/library/asyncio.html
3. **轮询等待 I2C 响应等忙等待**：改为 `await asyncio.sleep_ms()` 让步给事件循环。

修改驱动后，更新对应 Mock 的方法签名（`async def` 匹配），task 协程中用 `await` 调用。

## Phase 3: LLM 生成任务文件

读取 `manifest.requirements.description`（用户需求描述）和 `manifest.devices` 列表 → 生成 task 文件。

**约束（LLM 必须在生成代码中满足）：**

1. **纯函数 + DI**：task 是纯 Python 函数，不 `import machine`，所有硬件通过参数传入驱动对象
2. **独立异常处理**：每个传感器/器件的读写操作独立 try/except，一个挂了不影响其他
3. **print() 与 `lib.logger` 强制双写**：`install_rotating()` 会 monkey-patch 所有 logger 输出（包括 `debug()`/`info()`/`warning()`/`error()`）重定向到 `/log/run_*.log` 文件，REPL 完全看不到。因此 `print()` 是 REPL 唯一可见通道，必须严格遵守以下规则：

   **必须双写（logger + print 同时存在）的场景：**
   - 传感器/器件每次数据采集成功 → `debug(msg)` + `print(msg)`
   - 显示更新内容 → `debug(msg)` + `print(msg)`
   - 初始化/启动/调度器开始 → `info(msg)` + `print(msg)`
   - 异常/错误 → `warning/error(msg)` + `print(msg)`
   - 报警触发/恢复 → `warning/info(msg)` + `print(msg)`

   **不可双写（只用一处）的场景：**
   - I2C 扫描细节、驱动内部状态变更等非用户关心信息 → 只用 `debug()`
   - 临时调试打印（后续会删除） → 只用 `print()`

   日志消息需带模块标识前缀（如 `[sensor]`、`[display]`、`[alarm]`），具体格式由 LLM 自主决定
4. **温度键冲突处理**：当同时有温湿度传感器和气压传感器时，气压传感器的温度写入 `pressure_temp`，避免覆盖主温度
5. **无硬编码阈值**：所有阈值、间隔从 conf.py 导入
6. **装饰器**：timer 模式用 `@timed_function`，async 模式用 `@timed_coro`

**task 日志插入点（LLM 必须在对应位置插入，级别和具体措辞可自主调整）：**

| 位置 | 级别 | 双写 | 内容要求 |
|------|------|:---:|------|
| 传感器读取成功 | `debug` | **必须** | 含传感器名 + 实际读值。`debug(msg)` + `print(msg)` 缺一不可 |
| 传感器读取失败 | `warning` | **必须** | 含传感器名 + 异常信息。`warning(msg)` + `print(msg)` |
| 报警触发 | `warning` | **必须** | 含参数名 + 当前值 + 阈值。`warning(msg)` + `print(msg)` |
| 报警恢复 | `info` | **必须** | 含参数名 + 当前值。`info(msg)` + `print(msg)` |
| 显示更新 | `debug` | **必须** | 含当前显示内容摘要。`debug(msg)` + `print(msg)` |
| 显示更新失败 | `warning` | **必须** | 含异常信息。`warning(msg)` + `print(msg)` |
| 未预期 Exception | `error`/`exception` | **必须** | 含上下文（哪个 task、在处理什么数据）。logger + print 双写 |
| 纯内部状态（GC 统计、计数器递增等） | `debug` | 可选 | 用户不关心的内部细节，logger 记录即可，可不 print |

**LLM 自主决定：**
- 函数签名（参数名、驱动对象的顺序和数量）
- data dict 的键名和结构
- 业务逻辑流程（采集→处理→输出）
- 需要生成几个 task 文件（按功能拆分：传感器采集 / 报警 / 显示 / 网络等）

## Phase 4: LLM 补充 conf.py

用 `file_operation` 读取 scaffold 生成的 `firmware/conf.py`，按项目需求补充业务常量。

**约束：**

1. **阈值不硬编码**：所有告警阈值、校准偏移、刷新间隔等从 conf.py 导入，不在 task/main 中写死数值
2. **日志配置必须包含**：
   ```python
   LOG_DIR = "/log"
   LOG_MAX_FILES = 4
   LOG_LINES_PER_FILE = 150
   ```
3. 不放敏感数据（无 Wi-Fi 密码、API Key）

**日志消息原则（LLM 生成所有日志消息时遵守）：**

- **可检索性**：消息中应含模块名或关键字（如 `[sensor]`、`[alarm]`），方便在日志文件中搜索
- **可读性**：一行日志即可理解发生了什么，无需对照代码上下文
- **分级别**：`debug`=开发调试细节（可默认关闭）、`info`=关键流程节点、`warning`=可恢复异常、`error`/`critical`=不可恢复错误
- **含关键数据**：传感器日志带实际读值，报警日志带当前值和阈值，异常日志带异常类名和 message

**LLM 自主决定：** 根据 `manifest.requirements.description` 推断需要的常量名和值（告警阈值、校准值、显示间隔等），日志消息中的时间戳格式和模块标识前缀。

## Phase 5: LLM 生成 main.py（DI 装配 + 日志初始化）

读取所有工厂文件 + task 文件 + conf.py → 生成 main.py。

**约束：**

0. **启动延时（强制第一行代码）**：main.py 在 import 语句之后、任何业务逻辑之前，**必须**插入 3 秒启动延时，给设备软复位后 Blockless 设备会话重新枚举并建立连接的时间窗口：

```python
import time; time.sleep(3)  # Boot delay: allow the device session to reconnect after reset
```

这确保 deploy/autofix 的设备会话在 main.py 输出第一行日志之前就已连接，不会遗漏任何启动输出。

1. **DI 装配链**：`machine.I2C/Pin → 工厂 create_xxx() → 驱动对象 → task 函数参数`，完整串联
2. **I2C 地址冲突处理**：先尝试所有器件挂同一 I2C，地址冲突时创建第二个 I2C 实例
3. **日志必须初始化**：

```python
from lib.logger import install_rotating, getLogger, info, warning, error, setLevel, DEBUG, INFO
from conf import LOG_DIR, LOG_MAX_FILES, LOG_LINES_PER_FILE, LOG_LEVEL

# 安装轮转日志 —— 所有 logger 输出写入 /log/run_*.log
# fmt 参数由 LLM 自主决定，不指定则使用默认 "%(levelname)s:%(name)s:%(message)s"
install_rotating(LOG_DIR, max_files=LOG_MAX_FILES, lines_per_file=LOG_LINES_PER_FILE)

# 激活 conf.LOG_LEVEL —— install_rotating() 后 logger 输出只进文件，
# setLevel() 控制哪些级别真正写入（DEBUG 全量 / INFO 跳过 debug）
if LOG_LEVEL == 'DEBUG':
    setLevel(DEBUG)
else:
    setLevel(INFO)
_log = getLogger("main")
```

补一句 `print()` 输出固件名称+版本到 REPL，再 `info(...)` 写入日志。

**为什么 print() + 轮转日志两者都要：**
- `print()` → REPL 实时输出，设备会话连接时即时可见
- 轮转日志 → 写入设备端 `/log/run_*.log`，会话断开后仍可通过 `device_command` 文件读取回溯

4. **启动时 I2C 扫描**：对每个 I2C 器件调用 `scan_<name>_i2c(i2c)`，结果用 info/warning + print 双写

**main.py 日志插入点（LLM 必须在对应位置插入，级别和具体措辞可自主调整）：**

| 位置 | 级别 | 内容要求 |
|------|------|------|
| 固件启动 | `info` | 项目名 + 版本号 + 板名 |
| 轮转日志安装 | `debug`/`info` | LOG_DIR 路径 |
| I2C 总线初始化 | `info` | bus id + SCL/SDA pin 号 |
| 各驱动创建成功 | `info` | 驱动名 + I2C 地址 |
| 各驱动创建失败 | `warning` | 驱动名 + 异常信息 |
| I2C 扫描结果 | `info`/`warning` | 器件名 + found/missing |
| 调度器/事件循环启动 | `info` | tick_ms 或等效参数 |
| 调度器主循环异常 | `error` | 致命错误，含 traceback |

**LLM 自主决定：** import 组织、初始化顺序、`install_rotating(fmt=...)` 参数、启动日志具体措辞、GPIO/SPI 器件的创建方式。

## Phase 6: LLM 生成测试文件

### 6A: PC 端单元测试 `test/pc/test_<task>.py`

**约束（LLM 必须在生成代码中满足）：**

1. **至少覆盖三种场景**：正常数据、传感器缺失（传入 None）、传感器异常（驱动抛异常）
2. **导入 Mock 替换真实驱动**：`from drivers.<name>_driver.mock import Mock<Name>`
3. **用 `sys.path.insert(0, 'firmware')`** 确保能在 CPython 下导入 firmware/ 下的模块
4. **使用 CPython unittest**

**LLM 自主决定：** 测试类命名、Mock 参数配置、断言内容和数量、是否扩展更多边界用例。

### 6B: 设备端冒烟测试 `test/device/test_smoke.py`

只测硬件可用性，不测业务逻辑。

**只用 MicroPython unittest 支持的 assert 方法**（`assertTrue`、`assertEqual`、`assertIsNotNone`、`assertRaises`），**禁止使用** `assertIsInstance`、`assertIn`、`assertNotIn`、`assertGreater` 等 CPython 扩展。

```python
from machine import I2C, Pin
import unittest
from drivers.<name>_driver import scan_<name>_i2c

class TestSmoke(unittest.TestCase):
    def test_i2c_bus_scan(self):
        i2c = I2C(<bus_id>, scl=Pin(<scl>), sda=Pin(<sda>))
        devices = i2c.scan()
        self.assertTrue(len(devices) > 0, "No I2C devices found on bus")

    def test_<name>_present(self):
        i2c = I2C(<bus_id>, scl=Pin(<scl>), sda=Pin(<sda>))
        self.assertTrue(scan_<name>_i2c(i2c),
                        "<NAME> not found at expected address")
```

**LLM 自主决定：** 为每个 I2C 器件生成对应的 `test_<name>_present` 方法，添加 GPIO/SPI 器件的硬件测试。Pin 脚号从 manifest 读取。

### 6C: CPython 兼容性

PC 端测试（`test/pc/`）会遇到 MicroPython 特有模块在 CPython 不存在的问题。生成代码时应遵守架构约束（除 main.py 外不 import machine），但如果 lib/ 下的文件（如 logger、time_helper）使用了 `micropython.const`、`time.ticks_ms` 等 MPY 专有 API，需要确认它们有 CPython fallback。如果发现缺失，顺手补上。

## Phase 7: 验证（browser_validate + 兼容性检查）

### 7A: 客观校验

用 `browser_validate` 运行：
- `python_syntax`：`firmware/` 下所有 `.py`（排除 `firmware/lib/` 外部驱动）解析通过
- `generate_quality`：必需生成文件存在且非空
- `mpy_compile`：交叉编译检查（provider 未加载时返回 `partial`）

风格约定由 LLM 落实（行宽 ≤ 120、无未用 import、`raise`/`print` 字符串英文）。有错直接修，修完重新校验，直到通过。

### 7C: MicroPython 导入兼容性检查

**这是关键拦截点**：CPython 有大量内置模块（`logging`、`collections`、`typing`、`pathlib` 等），MicroPython 没有。PC 端测试通过不代表设备上能运行。

用 `file_operation` 列出 `firmware/` 下所有 `.py`（排除 `firmware/lib/`），逐文件提取顶层 `import X` 和 `from X import Y` 中的 `X`（忽略 `.` 开头的相对导入），逐一检查是否在已知 MicroPython 可用模块白名单中：

**MicroPython 内置 + stdlib 白名单（63 个）：**

```
sys, os, time, machine, micropython, gc, math, cmath, struct, json,
binascii, collections, errno, hashlib, io, platform, random, re, select,
socket, ssl, array, network, bluetooth, framebuf, uctypes, cryptolib,
deflate, btree, vfs, openamp, lcd160cr, neopixel, esp, esp32, espnow,
rp2, mimxrt, zephyr, wipy, stm, uasyncio, uarray, ubinascii, ucollections,
ucryptolib, uctypes, uerrno, uhashlib, uheapq, uio, ujson, uos, uplatform,
urandom, ure, uselect, usocket, ussl, ustruct, utime, uzlib, threading
```

对每个 X 做三层判断：

```
X 在白名单中？
  → 跳过（MPY 原生支持）

X 不在白名单，但 firmware/ 下存在 X.py 或 X/__init__.py？
  → 错误：应改为相对导入。示例：
    文件 firmware/tasks/my_task.py 中有 import logging
    → firmware/lib/logger/logging.py 存在
    → 修复为 from lib.logger import logging 或相对路径导入

X 不在白名单，firmware/ 下也不存在？
  → 警告：MicroPython 可能无此模块。LLM 判断是否需要替代方案
     常见陷阱：
       import typing        → MicroPython 不支持，删除类型注解导入
       import pathlib       → 改用 os.path / os.mkdir 等
       import dataclasses   → 改用普通类
       import collections   → 只用 list/dict（MPY 有 ucollections 但功能受限）
       import logging       → 用本项目的 lib.logger.logging
```

发现可自动修复的导入错误（同项目内有对应 .py 文件）→ 直接改，改完标注 `[FIX]`；不可自动修复的（无替代模块）→ 记录到审查清单，Phase 8 最终审查时处理。

### 7D: conf.py 死配置检测

**这是关键拦截点**：Phase 4 补充 `conf.py` 时可能加入常量，但 Phase 3 已生成的 task 文件未必引用。结果是配置项定义了但无人使用——"看起来有配置，实际不生效"。

LLM 执行步骤：

1. 提取 `conf.py` 中所有模块级 `UPPER_CASE = value` 常量名（排除 `__` 开头的 Python 内置变量）。
2. 对每个常量，扫描 `firmware/` 下所有 `.py`（排除 `firmware/lib/` 外部驱动和 `conf.py` 自身），检查是否被引用（`import conf` 后的 `conf.X`、`from conf import X`）。
3. 输出死配置清单（定义于 conf.py 但未被任何 firmware/*.py 引用）。
4. 对每个死配置两级处理：语义明确需要 → 修 task 文件让配置生效；无实际用途 → 从 conf.py 删除，保持配置干净。
5. 修复后重新检测，确认零死配置。

**典型陷阱（LLM 必须注意）：**
- scaffold 模板自带的基础常量（`LOG_DIR`、`SAMPLE_INTERVAL_MS` 等）不会被误判——它们一定被 main.py 或模板文件引用
- `conf.py` 中仅被 `test/` 目录引用的常量不算死配置——测试也算使用
- 静态配置值（如 I2C 地址、Pin 脚号）可能只在 `main.py` DI 装配阶段使用，不在 task 文件中出现——这正常

## Phase 8: AI 生成后审查

Phase 2-7 完成后，LLM 执行最终审查，逐项核验：

- **8A 驱动 API 正确性**：重新通读 `firmware/lib/*.py`，确认工厂 `__init__.py` 的 import 和构造调用与真实驱动一致；Mock 方法签名（参数名、返回值类型）与驱动源码匹配；所有公开方法都已 Mock。
- **8B 需求覆盖**：对照 `manifest.requirements.description`，确认每个需求点都有对应 task；`manifest.output` 列出的输出器件（display/buzzer/led）都有 task 和 main.py 装配。
- **8C GPIO 器件审查**：GPIO-only 器件（source=none）的工厂封装是否合理；Mock 是否覆盖 on/off/toggle/value。
- **8D 测试覆盖审查**：`test/pc/test_*.py` 覆盖正常 + 异常 + 边界（None）三种情况；`test/device/test_smoke.py` 只用 MPY unittest 允许的 assert。
- **8E MicroPython 导入兼容性审查**：复核 Phase 7C 扫描结果；重点检查 `firmware/lib/` 下外部驱动是否有 CPython 特有绝对导入（`import typing`/`import logging`）。
- **8F conf.py 死配置终审**：复核 Phase 7D 清单；特别注意 Phase 4 补充的"意图型"常量；判决保留+补实现 / 删除 / 标记为预留。
- **8G**：发现问题时直接修改对应文件，然后重新运行 Phase 7 校验 + 7C import 检查 + 7D 死配置检查和 PC 测试。

## Phase 9: 收尾（更新 manifest + phase_complete）

用 `file_operation` 将 `project-manifest.json` 的 `phase` 更新为 `generate`，记录 `generate.generated_at`，写回项目存储。然后发出 `phase_complete(phase="generate", next_phase="upy-deploy-browser")`，附带生成文件清单与校验证据。

## 参考文档

生成代码时遇到 API 不确定的情况，查阅以下权威文档：

| 文档 | URL | 用途 |
|------|-----|------|
| MicroPython 官方文档 | https://docs.micropython.org/en/latest/index.html | 所有 MPY 标准库 API 参考 |
| asyncio 协程 | https://docs.micropython.org/en/latest/library/asyncio.html | async 模式：`create_task`、`sleep_ms`、`gather`、`Event`、`Queue` 等 |
| _thread 多线程 | https://docs.micropython.org/en/latest/library/_thread.html | _thread 模式：`start_new_thread`、`allocate_lock`、`exit` 等 |

## 架构约束（生成代码必须遵守）

- **鸭子类型 DI**：task 函数接收对象，不关心是真实驱动还是 Mock
- **除 main.py 外不 import machine**：所有 .py 文件不直接 import machine.Pin/I2C/SPI/UART
- **除 lib/ 外不使用 typing 泛型**：类型注解只用 MPY 内置类型
- **独立 try/except**：每个 task_tick 独立异常处理，一个传感器挂了不影响其他
- **阈值在 conf.py**：不硬编码数值
- **Mock 方法签名与真实驱动一致**：通过阅读驱动源码和 example.py 确认
- **所有 I2C 驱动工厂必须导出 `scan_<name>_i2c(i2c, address)` 函数**：不依赖驱动实例，仅扫描 I2C 总线检查地址是否存在，为后续调试/部署 skill 提供硬件连通性判断依据。软件可配置地址的器件（如 GT911）需查阅 example.py 确定检测策略
- **日志写入设备文件系统**：main.py 启动时安装轮转日志（`lib.logger.install_rotating`）。关键流程节点 `print()` + `lib.logger` 双写（REPL 即时可见 + 设备端持久化）；纯调试细节可只用 `print()`。即使会话断开，日志仍可通过 `device_command` 读取设备端文件

## 成功契约与安全规则（domain）

**用户补充的路由**：运行前可询问用户补充业务行为/阈值/周期/状态机/日志/模拟场景；但**新增硬件或改引脚必须回退**到 analyze/select-hw/scaffold，不在 generate 内擅自加硬件。

**云 / 第三方 API 安全**：需求涉及 LLM/ASR/TTS/视觉/IoT-MQTT/Webhook/REST 等付费或带凭据的云服务时，必须经 `approval_request` 让用户确认：服务商、官方文档/控制台/价格链接、是否已开通计费、API Key 是否就绪、是否需要网关/代理。**真实 token 绝不写入代码**；`conf.py` 只存非密钥 endpoint、模型名、超时、重试、功能开关与 secret 名称。云服务为 `mock_only` 或 `blocked` 时**不得进入 deploy**，并在 `manifest_content.generate.cloud_integrations[]` 记录。

**外设 API 文档证据**：用到 `machine`/`network`/`neopixel`/`esp32`/`rp2`/`bluetooth` 等硬件外设 API，必须在 `manifest_content.generate.doc_evidence[]` 记录 `module` + 官方 MicroPython `url` + `reason`；仅 CPython 链接或页面内容不足 → 补端口文档证据或输出 partial。

**部署就绪契约（success 必须满足）**：

- `runtime_dependencies.mip`：生成的固件/设备测试需要 mip 包（如设备端 `unittest`）时必须声明，deploy 阶段用 `mip install` 安装，不把 micropython-lib 源码 vendor 进项目。
- `deploy_plan.source_only` = `firmware/main.py`、`firmware/boot.py`、`firmware/conf.py`（这三个以 `.py` 部署）；`deploy_plan.upload_exclude` = `firmware/drivers/**/mock.py`、`firmware/drivers/**/mock.mpy`。Mock 是测试替身，**绝不作为运行时固件**。
- 设备端测试默认放 `device/tests/`，验证协议/状态/任务/驱动/配置契约，不只是 import smoke。
- success 不得遗留或提交 CPython 缓存（`__pycache__/`、`*.pyc`）。
- 语音/传感器/云/状态机等跨 tick 业务流，`generate_plan` 必须声明 `data_flow_contract[]`（producer/consumer/invariant/storage）并为关键数据流生成 contract test。

**partial/failed 判定**：`NETWORK_DISCONNECTED`、`RATE_LIMITED`、`UPSTREAM_TIMEOUT` 视为可重试中断；`TOKEN_BUDGET_EXCEEDED`、`MODEL_CONTEXT_EXHAUSTED`、`CANCELLED_BY_USER` 非可重试（除非用户改预算/模型/意图）。校验或最终一致性检查失败 → 改 `partial`/`failed`、`next_phase=null` 并记录 structured error。

## 与其他 skill 的关系

- ← `upy-scaffold-browser`：输入骨架 + manifest
- → `upy-deploy-browser`：上传代码到设备并验证
- → `upy-wiring-browser`：引脚分配表 → 接线图
- → `upy-diagram-browser`：代码结构 → 架构图

## 强约束

- **可以修改 lib/ 下的驱动源码**（仅限：①添加 DI 支持如 i2c=None 参数 ②修复非标准换行符），修改前经 `approval_request` 确认
- **不生成全局 firmware/mock/ 目录**
- **async 模式下驱动默认不改**，但如果驱动存在阻塞式方法（`time.sleep`、I2S 阻塞操作等），必须修改为异步版本并查阅 asyncio 官方文档确认 API；异步化也可在封装层处理
- **生成结束自动 `browser_validate` 校验 + PC 测试运行**，不通过不结束
- **lib/ 下文件需保证 CPython 兼容**：`micropython.const`、`time.ticks_ms` 等 MPY 专有 API 要有 fallback（logger、time_helper 等 scaffold 文件可能遗漏）
- **设备端测试只用 MPY unittest assert 子集**：`assertTrue`、`assertEqual`、`assertIsNotNone`、`assertRaises`，禁止 `assertIn`/`assertIsInstance` 等
