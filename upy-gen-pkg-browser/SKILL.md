---
name: upy-gen-pkg-browser
description: Use when generating a package.json from scratch for a MicroPython driver package inside Blockless Web Builder. Triggers like "generate package.json", "生成package.json", "创建mip包配置", or a driver dir/file provided to create a package config.
---

# upy-gen-pkg-browser

## Purpose

Generate a complete, spec-compliant `package.json` (upypi/mip format) from scratch by analyzing a driver package's structure and dependencies, resolving third-party deps via the Blockless package provider. Generation is performed by the LLM applying the rules below. Blockless Web Builder is the only target runtime for this browser skill.

## Plugin Equivalence

Equivalent source skill:
- `upy-gen-pkg`

This browser contract preserves the source skill's responsibility, field rules, dependency-resolution logic, and failure semantics. Source-side `curl`/`mpremote` package queries and local file write are replaced by Blockless primitives only:
- `file_operation`
- `approval_request`
- `browser_validate`
- `phase_complete`

Validation kinds retained for this skill:
- `upypi_resolve`
- `package_resolve`
- `project_files`

## Inputs

- Blockless project id and project store snapshot.
- The project-store path of the driver directory or `.py` file.
- upypi resolution results returned by the loaded Blockless package provider.

## Outputs

- The generated `package.json`, written to the Blockless project store after user approval.
- The three install commands for the package.
- `phase_complete` for `upy-gen-pkg` with `status`, `evidence`, `artifacts`, and a recoverable `next_action` when needed.

## Blockless Primitive Sequence

1. `file_operation`: read the driver files and detect sub-package directories.
2. `browser_validate` (`upypi_resolve`, `package_resolve`): resolve each third-party / sub-package dependency (returns `partial` until a package provider is loaded).
3. Apply the field + dependency rules below (LLM-driven; see the domain/validate boundary section).
4. `browser_validate` (`project_files`): confirm the output path is project-relative.
5. `approval_request` + `file_operation`: confirm and write `package.json` to the project store.
6. `phase_complete`: return status, evidence, and artifacts.

## Runtime State And Partial Results

- `phase_complete.status` is `success`, `partial`, or `failed`.
- Missing runtime state returns a partial envelope such as:

```json
{
  "status": "partial",
  "phase": "upy-gen-pkg",
  "capability_required": "browser_validate.upypi_resolve",
  "next_action": "load_provider"
}
```
- `capability_required` describes missing Blockless runtime state or provider registration, not a browser limitation.

## Failure Conditions

- Return `failed` when the driver files are missing/malformed or required fields cannot be produced.
- Return `partial` when the Blockless package provider, project-store access, or user approval is missing.
- Include `capability_required` (`browser_validate.<kind>` / `file_operation.<action>`) and `next_action` (`load_provider`/`sign_in`/`grant_file_access`).
- Do not bypass Blockless primitives for local execution paths.

## Domain Generation vs browser_validate (boundary)

Field generation is the LLM applying the rules below; dependency resolution goes through the Blockless package provider (`upypi_resolve`/`package_resolve`). `browser_validate` performs only the objective subset (resolve + path validity); it does **not** decide the package shape. Blockless Web Builder runs both.

## 角色定位

你是 GraftSense MicroPython 包配置生成助手。给定一个驱动目录或驱动 `.py` 文件，分析其结构和依赖，从 0 生成符合 GraftSense 规范的完整 `package.json`。

## 执行步骤

1. 扫描用户指定目录：
   - **1a**：扫描所有顶层 `.py` 文件，排除 `main.py`，作为驱动文件列表；**必须重新读取每个文件的完整内容，不得使用会话缓存或跳过读取步骤**
   - **1b**：扫描所有含 `__init__.py` 的子目录，作为**子包依赖候选列表**
2. 子包依赖处理（见"子包依赖处理"章节）
3. 从所有驱动文件中提取：文件名列表、`@Author`、`@Description`、`__version__`、`__license__`、所有 `import` 语句（合并去重）；`author`/`version`/`description` 优先从与目录同名的主驱动文件提取，若无同名文件则从第一个 `.py` 文件提取
4. 分析每个 import 的来源类型（见依赖处理步骤）
5. 对第三方依赖逐一查询 upypi
6. 生成完整 `package.json`

## 必须生成的字段（全部）

| 字段 | 生成规则 |
|---|---|
| `name` | 从目录名提取，转为小写字母+下划线（如 `BH1750_driver` → `bh1750_driver`） |
| `urls` | 扫描目录下所有**顶层** `.py` 文件（排除 `main.py`），每个文件生成一条 `["文件名.py", "code/文件名.py"]` 映射；含 `__init__.py` 的子目录根据开发者选择：选②打包进 urls（含子目录路径前缀），选①③则不写入 `urls` |
| `version` | 从 `__version__` 提取，若无则默认 `"1.0.0"` |
| `_comments` | 固定内容（见下方模板） |
| `description` | 从 `@Description` 或类 docstring 提取，英文 |
| `author` | 从驱动文件 `__author__` 或文件头 `@Author` 提取；若无则提示用户填写，不得使用占位符 |
| `license` | 从 `__license__` 提取，默认 `"MIT"` |
| `chips` | 默认 `"all"`，除非驱动明确依赖特定芯片（如 RP2040 PIO） |
| `fw` | 默认 `"all"`，除非有特殊固件依赖（ulab、lvgl 等） |

## 子包依赖处理

对步骤 1b 扫描到的每个含 `__init__.py` 的子目录，按以下流程处理：

### 有子包目录时

**用 `browser_validate` 的 `upypi_resolve` 解析子目录名**（已加载的 Blockless 包提供方查询 upypi；未加载时返回 `partial`，next_action=`load_provider`）：

- **有结果**：将返回的 url 写入 `deps`：`["{url}", "latest"]`
- **无结果**：询问开发者：
  ```
  发现子包目录 `{子目录名}/`（含 __init__.py），upypi 暂无收录。
  请选择处理方式：
  ・① 发布为独立包 → 建议先完成 upypi 发布，再生成 package.json
  ・② 打包进本驱动 urls → 将子目录下所有文件逐条写入 urls
  ・③ github 占位 → 写入 deps，标注 ⚠️ 需手动确认
  ```
  - 选 **①**：暂停，待用户完成发布后继续
  - 选 **②**：扫描该子目录下所有 `.py` 文件（含子层级），按如下格式逐条追加到 `urls`：
    ```json
    ["{子目录名}/文件名.py", "code/{子目录名}/文件名.py"]
    ```
    示例（sensor_pack_2 有 3 个文件）：
    ```json
    ["sensor_pack_2/__init__.py",    "code/sensor_pack_2/__init__.py"],
    ["sensor_pack_2/base_sensor.py", "code/sensor_pack_2/base_sensor.py"],
    ["sensor_pack_2/bus_service.py", "code/sensor_pack_2/bus_service.py"]
    ```
    此时 `deps` 中不写入该子包。
  - 选 **③**：写入 `deps`：`["github:FreakStudioCN/{子目录名}", "main"]`，标注 ⚠️
- **provider 未就绪（partial）**：upypi 解析需要 Blockless 包提供方；未加载时返回 partial（next_action=`load_provider`），视同"无结果"分支，展示三选项询问开发者

### 无子包目录时

在输出 `package.json` 之前询问开发者：
```
当前目录未检测到子包依赖目录。
若驱动依赖的工具模块（如 bus_service、base_sensor 等）未来需要供其他驱动复用，
是否考虑将其单独整理为 Python 包发布到 upypi？
（当前可跳过，继续生成 package.json）
```

## 依赖处理（三步优先级）

### 第一步：识别 import 来源

```
MicroPython 内置模块（machine、time、sys、utime、uos、ustruct 等）
→ 不写入 deps，直接跳过

micropython-lib 标准库（collections、os、json、re、hashlib 等）
→ 用 mip 标准格式：["库名", "latest"]

其他第三方模块（非上述两类）
→ 进入第二步查询 upypi
```

### 第二步：查询 upypi

对每个第三方依赖，用 `browser_validate` 的 `upypi_resolve` 解析（已加载的 Blockless 包提供方查询 upypi）：

响应示例：
```json
{"query":"ds18b20","results":[{"name":"ds18b20_driver","url":"https://upypi.net/pkgs/ds18b20_driver/1.0.0"}]}
```

- **有结果**：使用返回的 `url` 字段写入 deps：`["{url}", "latest"]`
- **provider 未就绪（partial）**：upypi 解析需要 Blockless 包提供方；未加载时返回 partial（next_action=`load_provider`），按"无结果"处理
- **无结果**：用 `github:` 占位格式写入，并在文件末尾标注 `⚠️ 需手动确认`

### 第三步：deps 字段格式

```json
"deps": [
  ["https://upypi.net/pkgs/ds18b20_driver/1.0.0", "latest"],
  ["collections-defaultdict", "latest"],
  ["github:org/repo", "main"]
]
```

若无任何外部依赖，省略 `deps` 字段。

## 许可证与版权规则

| 情况 | author 字段 | license 字段 |
|---|---|---|
| 参考他人开源代码 | 与原仓库作者一致 | 与原仓库许可证一致 |
| FreakStudio 原创 | `"leeqingshui"` 或团队名 | `"MIT"` |

**参考他人代码示例**（如参考 robert-hh 的 bmp280 驱动）：
```json
{
  "name": "bmp280_driver",
  "urls": [["bmp280_float.py", "code/bmp280_float.py"]],
  "version": "1.0.0",
  "_comments": {
    "chips": "该包支持运行的芯片型号，all表示无芯片限制",
    "fw": "该包依赖的特定固件如ulab、lvgl,all表示无固件依赖"
  },
  "description": "A MicroPython library to control BMP280 pressure sensor",
  "author": "robert-hh",
  "license": "MIT",
  "chips": "all",
  "fw": "all"
}
```
> author 和 license 字段必须与原仓库保持一致，不得填写 FreakStudio 信息。

## 输出模板

```json
{
  "name": "sensor_driver",
  "urls": [
    ["sensor.py", "code/sensor.py"]
  ],
  "version": "1.0.0",
  "_comments": {
    "chips": "该包支持运行的芯片型号，all表示无芯片限制",
    "fw": "该包依赖的特定固件如ulab、lvgl,all表示无固件依赖"
  },
  "description": "A MicroPython library to control [传感器名称]",
  "author": "作者名",
  "license": "MIT",
  "chips": "all",
  "fw": "all"
}
```

有依赖时追加 `deps` 字段（置于 `urls` 之前）：
```json
{
  "name": "xfyun_asr",
  "version": "1.0.1",
  "description": "iFlytek online ASR WebSocket driver for MicroPython",
  "author": "leeqingsui",
  "license": "MIT",
  "chips": "all",
  "fw": "all",
  "_comments": {
    "chips": "该包支持运行的芯片型号，all表示无芯片限制",
    "fw": "该包依赖的特定固件如ulab、lvgl,all表示无固件依赖"
  },
  "deps": [
    ["https://upypi.net/pkgs/async_websocket_client/1.0.0", "latest"]
  ],
  "urls": [
    ["xfyun_asr.py", "code/xfyun_asr.py"]
  ]
}
```

## 三种安装方式（生成 package.json 后告知用户）

生成完成后，附上对应该包的三种安装命令供用户参考：

```python
# 方式一：mip（在设备上运行）
import mip
mip.install("github:FreakStudioCN/GraftSense-Drivers-MicroPython/sensors/{包目录名}")

# 方式二：upypi（推荐，访问 https://upypi.net/ 搜索包名获取命令）
```

## 输出格式

1. 输出完整的 `package.json` 内容（JSON 代码块预览）。
2. 询问用户："确认写入同目录下的 `package.json` 吗？"，用户确认后将内容写入文件。

若存在 upypi 查询无结果的依赖，在代码块之后单独列出：
```
⚠️ 以下依赖未在 upypi 找到，已使用占位格式，请手动确认：
- {模块名}：github:org/repo
```

最后附三种安装方式命令（替换 `{包目录名}` 为实际目录名）。


## 完整规范参考

本 Skill 的字段规则基于 GraftSense 驱动编写规范文档（22 章、2200+ 行），已随本仓库附带，按相对路径查阅：

[docs/reference/upy_driver_dev_spec_summary.md](../docs/reference/upy_driver_dev_spec_summary.md)
