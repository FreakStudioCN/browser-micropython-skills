---
name: upy-pkg-guide-browser
description: Use when a device/chip name is mentioned and the user wants to know how to use its MicroPython driver inside Blockless Web Builder. Triggers like "怎么用BMP280", "DS18B20怎么调用", "查一下upypi上XX的驱动怎么用", or any chip/sensor name with a usage question.
---

# upy-pkg-guide-browser

## Purpose

Given a device name, look up its MicroPython driver (upypi → awesome-micropython, via the Blockless package/document provider), analyze the package, and output the usage essentials (constructor, public API, I2C default address, return types). A shared lookup tool, used by `upy-analyze-browser` and `upy-project-browser`. Blockless Web Builder is the only target runtime for this browser skill.

## Plugin Equivalence

Equivalent source skill:
- `upy-pkg-guide`

This browser contract preserves the source skill's lookup priority and extraction rules. The source-side HTTP CLI and device install commands are replaced by Blockless primitives only:
- `file_operation`
- `browser_validate`
- `phase_complete`

Validation kinds retained for this skill:
- `package_fetch`
- `doc_fetch`
- `awesome_micropython_search`

## Inputs

- The device/chip name.
- Package/document results returned by the loaded Blockless provider.

## Outputs

- A one-page API cheat sheet (package info, install commands, init example, core API table, notes).
- `phase_complete` (when invoked as a step) with `status`, `evidence`, and a recoverable `next_action` when needed.

## Blockless Primitive Sequence

1. `browser_validate` (`package_fetch` / `awesome_micropython_search`): search upypi then awesome-micropython for the device.
2. `browser_validate` (`doc_fetch`): fetch the package.json + driver `.py` + README + example (returns `partial` until the provider is loaded).
3. Extract the usage essentials per the rules below (LLM-driven).
4. `phase_complete`: return the cheat sheet.

## Runtime State And Partial Results

- Status is `success`, `partial`, or `failed`.
- Missing runtime state returns a partial envelope such as:

```json
{
  "status": "partial",
  "capability_required": "browser_validate.package_fetch",
  "next_action": "load_provider"
}
```
- `capability_required` describes a missing Blockless package/network provider, not a browser limitation.

## Failure Conditions

- Return `failed` when no driver is found in either source.
- Return `partial` when the package/document provider is not loaded.
- Include `capability_required` (`browser_validate.<kind>`) and `next_action` (`load_provider`/`sign_in`).
- Do not bypass Blockless primitives for local execution paths.

## 角色定位

给定一个器件名称，按优先级依次从 **upypi → awesome-micropython** 查找驱动，综合分析后输出使用要点。

---

## 执行步骤

### 第一步：搜索 upypi

```bash
browser_validate doc_fetch "https://upypi.net/api/search?q={器件名}"
```

- 有结果 → 进入 **upypi 路径**（第二步 A）
- 无结果 → 进入 **awesome-micropython fallback 路径**（第二步 B）

---

### 第二步 A：upypi 路径

#### 获取 package.json

```bash
browser_validate doc_fetch "{package_url}/package.json"
```

提取：`urls`（驱动文件列表）、`version`、`author`、`description`、`deps`

#### 并行下载文件

base_url = `https://upypi.net/pkgs/{name}/{version}/`

| 文件 | URL |
|---|---|
| 驱动 .py（来自 urls） | `{base_url}{source_path}` |
| main.py | `{base_url}code/main.py` |
| README.md | `{base_url}README.md` |

404 则跳过，不报错。

→ 跳至**第三步：综合分析**

---

### 第二步 B：awesome-micropython fallback 路径

upypi 无结果时执行此路径。

#### 调用搜索

用 `browser_validate` 的 `awesome_micropython_search` kind 以 `{器件名}` 为查询搜索 awesome-micropython（provider 未加载时返回 `partial`）—— 不调用本地脚本或 host Python。

provider 返回 JSON，格式：
```json
{
  "query": "spacecan",
  "results": [
    {
      "name": "micropython-spacecan",
      "url": "https://gitlab.com/alphaaomega/micropython-spacecan",
      "desc": "...",
      "category": "Communications",
      "subcategory": "CAN"
    }
  ]
}
```

**处理逻辑：**
- `results` 为空 → 告知用户该器件在 upypi 和 awesome-micropython 均未找到，结束
- 有多个结果 → 列出所有条目（名称 + 描述），询问用户选哪个
- 只有一个结果 → 直接使用

#### 根据仓库平台拉取文件

根据 `url` 字段判断平台，拉取 README.md、main.py 及驱动 .py：

**GitHub 仓库：**
```bash
# 列举仓库文件
browser_validate doc_fetch "https://api.github.com/repos/{owner}/{repo}/contents/"
# 下载文件
browser_validate doc_fetch "https://raw.githubusercontent.com/{owner}/{repo}/master/{path}"
# 获取 README
browser_validate doc_fetch "https://raw.githubusercontent.com/{owner}/{repo}/master/README.md"
# 获取 main.py
browser_validate doc_fetch "https://raw.githubusercontent.com/{owner}/{repo}/master/main.py"
```

**GitLab 仓库：**
```bash
# 列举仓库文件（recursive=true 获取子目录）
browser_validate doc_fetch "https://gitlab.com/api/v4/projects/{namespace}%2F{project}/repository/tree?recursive=true"
# 下载文件
browser_validate doc_fetch "https://gitlab.com/{namespace}/{project}/-/raw/master/{path}"
# 获取 README
browser_validate doc_fetch "https://gitlab.com/{namespace}/{project}/-/raw/master/README.md"
# 获取 main.py
browser_validate doc_fetch "https://gitlab.com/{namespace}/{project}/-/raw/master/main.py"
```

优先下载：`README.md`、`main.py`、以及所有 `.py` 驱动文件（排除 `main.py` 和测试文件）。

→ 进入**第三步：综合分析**

---

### 第三步：综合分析，输出使用要点

综合已获取的文件，输出以下结构：

---

## {器件名} 驱动使用要点

**来源**
- 平台：`upypi` / `awesome-micropython ({category} > {subcategory})`
- 仓库：{url}
- 描述：{desc}

**安装**

upypi 路径：
```bash
device_command mip install {package_url}/package.json
```

awesome-micropython 路径（无标准包，手动复制）：
```bash
# 将以下文件复制到设备
device_command cp {driver_file}.py :{driver_file}.py
# 若有子包目录
device_command cp -r {pkg_dir}/ :{pkg_dir}/
# 若有依赖子目录（如 lib/）
device_command cp -r lib/ :lib/
```

**初始化**
```python
# 来自 main.py 的最小可运行示例
```

**核心 API**

| 方法/属性 | 参数 | 返回值 | 说明 |
|---|---|---|---|
| ... | ... | ... | ... |

**注意事项**
- 从 README.md 提取的关键限制、硬件接线、兼容性说明

---

## 输出原则

- `main.py` 是**第一优先**参考，直接展示其初始化代码作为最小示例
- `README.md` 补充注意事项和硬件接线
- 驱动 `.py` 用于提取完整 API 表格
- awesome-micropython 路径的包通常无标准化安装方式，需说明手动复制哪些文件/目录
- 若某文件不存在（404 或 API 无返回），跳过对应部分，不报错

## 搜索说明

awesome-micropython 索引搜索由 `browser_validate` (`awesome_micropython_search`) 提供：
- 自动拉取并缓存 `mcauser/awesome-micropython` 的 README（约 24 小时缓存）
- 大小写不敏感搜索库名和描述
- 支持平台：GitHub、GitLab、Codeberg
