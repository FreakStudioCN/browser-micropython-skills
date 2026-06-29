---
name: upy-diagram-browser
description: Software-diagram generation inside Blockless Web Builder. Reads firmware/ code + manifest, the LLM fills an intermediate JSON, and renders Mermaid architecture/flow/data-flow diagrams (.md/SVG/PNG/HTML). Triggers after upy-generate-browser.
---

# upy-diagram-browser

## Purpose

Generate architecture + flow + data-flow diagrams: read `firmware/` code and the manifest, have the LLM analyze structure/control/data flow and fill an intermediate JSON, then render Mermaid (.md) + SVG + PNG + HTML. The LLM reads the code and fills the JSON; `browser_validate` validates and renders. Blockless Web Builder is the only target runtime for this browser skill.

## Plugin Equivalence

Equivalent source skill:
- `upy-diagram`

This browser contract preserves the source skill's responsibility, `diagram.schema.json`, complexity tiers, and render outputs. Source-side local render scripts are replaced by Blockless primitives only:
- `file_operation`
- `browser_validate`
- `phase_complete`

Validation kinds retained for this skill:
- `diagram_mermaid`
- `diagram_render`

## Inputs

- Blockless project id, project store snapshot, the `firmware/` tree, and the manifest.
- Validation inputs for: `diagram_mermaid`, `diagram_render`.

## Outputs

- artifacts/diagram.* — the rendered Mermaid `.md` / SVG / PNG / HTML in the project store.
- `phase_complete` for `upy-diagram` with `status`, `evidence`, `artifacts`, and a recoverable `next_action` when needed.

## Blockless Primitive Sequence

1. `file_operation`: read the `firmware/` code (main.py, tasks/*, conf.py) and the manifest.
2. Fill the intermediate diagram JSON per the rules below (LLM-driven; see the domain/validate boundary section).
3. `browser_validate` (`diagram_mermaid`, `diagram_render`): validate and render the Mermaid/SVG/PNG/HTML outputs.
4. `file_operation`: write the rendered artifacts to the project store.
5. `phase_complete`: return status, evidence, and artifacts.

## Runtime State And Partial Results

- `phase_complete.status` is `success`, `partial`, or `failed`.
- Missing runtime state returns a partial envelope such as:

```json
{
  "status": "partial",
  "phase": "upy-diagram",
  "capability_required": "browser_validate.diagram_render",
  "next_action": "load_provider"
}
```
- `capability_required` describes missing Blockless runtime state (e.g. the render provider), not a browser limitation.

## Failure Conditions

- Return `failed` when required code/manifest data is missing or the diagram JSON fails schema validation.
- Return `partial` when the render provider or project-store access is missing.
- Include `capability_required` (`browser_validate.<kind>`) and `next_action` (`load_provider`/`sign_in`).
- Do not bypass Blockless primitives for local execution paths.

## Domain Authoring vs browser_validate (boundary)

Reading code and filling the diagram JSON is the LLM's job. `browser_validate` performs only the objective subset — schema validation and Mermaid/image rendering (`diagram_mermaid`, `diagram_render`). It does **not** decide the diagram content. Blockless Web Builder runs both.

## 角色定位

给定 `project-manifest.json`（phase: generate）和 `firmware/` 下所有 `.py` 文件，LLM 理解 `diagram.schema.json` 后分析代码结构、执行流程、数据流向，填入中间 JSON，再由脚本校验并生成 Mermaid 文本图（Markdown 代码块）+ SVG + PNG + HTML。**Mermaid .md + SVG + PNG + HTML 均为必需输出，脚本默认 --format all。LLM 负责阅读代码并填写 JSON，脚本只做校验和渲染。**

---

## 前置检查

无需本地环境：schema 校验与 Mermaid 渲染都通过 `browser_validate` 的 `diagram_mermaid` / `diagram_render` 完成（渲染由 Blockless provider 负责，未加载时返回 `partial`）。

---

## 执行步骤

### Step 0: 选择复杂度级别

**在执行任何分析之前，先询问用户需要的架构图复杂度。** 复杂度控制下面所有约束参数的上限，影响图的精简程度。

```python
AskUserQuestion(
  questions=[{
    "question": "架构图需要哪种复杂度？",
    "header": "架构图复杂度",
    "options": [
      {"label": "简单", "description": "高度精简，只保留核心模块/依赖/步骤，适合快速浏览"},
      {"label": "中等 (推荐)", "description": "平衡信息量和可读性，适合日常开发和沟通"},
      {"label": "详细", "description": "完整展开，模块/步骤/数据流全部保留，适合复杂项目或归档文档"}
    ],
    "multiSelect": False
  }]
)
```

**参数对照表（LLM 以选中档位为约束上限）：**

| 参数 | 简单 | 中等（默认） | 详细 |
|------|:----:|:--------:|:----:|
| `architecture` 总模块数 | ≤6 | ≤10 | ≤16 |
| 每层模块上限 | ≤2 | ≤4 | ≤6 |
| `cross_layer_deps` 总边数 | ≤6 | ≤12 | ≤20 |
| `cross_layer_deps[].label` | ≤4 字 | ≤6 字 | ≤10 字 |
| `role` | ≤8 字 | ≤10 字 | ≤14 字 |
| `flow[]` 总步数 | ≤5 | ≤8 | ≤14 |
| `flow[].action` | ≤4 字 | ≤6 字 | ≤8 字 |
| `flow[].detail` | ≤8 字 | ≤12 字 | ≤16 字 |
| `data_flow[]` 总边数 | ≤2 | ≤4 | ≤8 |
| `data_flow[].data` | ≤6 字 | ≤8 字 | ≤12 字 |

**选择后 LLM 严格按对应栏位的数值作为上限**，Step 3 中所有约束描述均以选中档位为准。默认：中等。

### Step 1: LLM 阅读 Schema → 理解结构

读取中间 JSON schema（仓库 `contracts/` 下的 diagram schema）。

理解 4 个必需字段：`meta`, `architecture`, `flow`, `data_flow`，以及可选字段 `task_registry`, `diagnostics`。

### Step 2: LLM 阅读源代码 → 分析结构

读取以下所有文件（每个文件必须通读）：

```
{project_dir}/project-manifest.json
{project_dir}/firmware/main.py            ← 入口：DI 装配链 + 流程步骤
{project_dir}/firmware/conf.py            ← 配置常量
{project_dir}/firmware/board.py           ← 板级 pin 常量映射
{project_dir}/firmware/boot.py            ← 启动代码
{project_dir}/firmware/lib/               ← 基础库（logger/scheduler/time_helper 等）
{project_dir}/firmware/drivers/           ← 驱动工厂 + mock（每个 driver 一个包）
{project_dir}/firmware/tasks/             ← 业务 task 文件
```

### Step 3: LLM 分析并填写 diagram.json

#### 3A: `meta` — 元数据

从 manifest 提取：`project`, `mode`, `mcu`, `source_phase`。
`generated_at` 填当前 UTC 时间（ISO 8601）。

#### 3B: `architecture.layers[]` — 分层架构

**层定义（自下而上）：**

| 层 ID | label | 包含哪些模块 |
|-------|-------|-------------|
| `board` | 板级层(Board) | `board.py` — pin 常量映射 |
| `lib` | 基础库(Library) | `lib/` 下所有 .py：logger, scheduler, time_helper 等 |
| `driver` | 驱动层(Driver) | `drivers/<name>_driver/__init__.py` — 各器件工厂 |
| `task` | 任务层(Task) | `tasks/*.py` — 业务 task 函数 |
| `entry` | 入口层(Entry) | `main.py` — DI 装配入口 |
| `test` | 测试层(Test) | `test/pc/*.py` — PC 端测试；`test/device/*.py` — 设备端测试 |

可选附加层：`host`（`host/` 下有代码时）。

**每个 module 对象：**
- `name`：Python import 路径，如 `tasks.sensor_task`
- `path`：相对文件路径，如 `firmware/tasks/sensor_task.py`
- `role`：模块职责的中文简述，上限以 Step 0 所选档位为准（从 docstring 首行提取，无 docstring 则 LLM 补写。节点框宽度有限，过长文本会导致节点膨胀、布局拥挤）
- `provides`：导出的函数名/类名列表（从 `def` / `class` 提取，排除 `_` 前缀的私有符号）
- `depends_on`：依赖的模块名列表（从 `import` / `from X import` 提取，排除 `machine` 和标准库）
- `depends_on_machine`：是否直接 `import machine`（true 仅 main.py）
- `has_mock`：`drivers/<name>_driver/mock.py` 是否存在
- `is_generated`：文件是否由 upy-generate 生成（`@Generated : upy-generate` 标记）
- `is_template`：文件是否来自 scaffold 模板
- `source`：来源枚举（`scaffold_template` / `llm_generated` / `upypi_download` / `github_download` / `cold_driver` / `user_custom`）

**LLM 自主决定：**
- 是否拆分一个 task 文件为多个 module（如果一个 task 文件有多个独立功能）；但模块总数、每层上限、跨层依赖边数和标签长度均以 Step 0 所选复杂度档位为上限，超出时合并功能相近的模块
- `cross_layer_deps[].label`：边标签上限以 Step 0 所选档位为准（如 "导入"、"注入"、"日志"；过长的边标签会使连线拥挤难以辨认）
- `cross_layer_deps[].style`：solid（直接依赖）/ dashed（DI 注入依赖）/ dotted（测试依赖）
- **16:9 比例预演：每写入一个模块/边/步骤，确认在 16:9 画布内各方向元素不超过容纳量 70%，否则合并或删除**

#### 3C: `flow[]` — 执行流程

从 `main.py` 提取执行步骤序列，每一步：

- `seq`：从 1 开始的序号
- `phase`：步骤阶段
  - `boot` → 启动延时、WDT 设置
  - `init` → I2C/SPI 总线初始化、日志初始化
  - `scan` → I2C 器件扫描（`scan_xxx_i2c()`）
  - `create` → 驱动实例创建（`create_xxx()`）
  - `assembly` → DI 装配（驱动注入 task）
  - `run` → 调度器启动 / 事件循环运行
  - `shutdown` → 清理（如存在）
- `action`：中文简短标题，上限以 Step 0 所选档位为准（如 "初始化 I2C"；时序图参与者宽度有限，过长文本会被截断）
- `detail`：具体参数，上限以 Step 0 所选档位为准（I2C 地址、Pin 脚号、频率等；会在 action 下方折行显示）
- `source_line`：在 main.py 中的行号
- `depends_on_step`：前置步骤 seq（如 create 依赖 scan 成功）
- `on_error`：失败策略（`fatal` 终止 / `skip_device` 跳过该器件继续 / `retry` 重试 / `degrade` 降级运行）
- `is_conditional` + `branches`：条件分支（如 scan 成功→create，失败→skip）

**LLM 自主决定：** 步骤粒度（一个 init 动作可拆成多步或合并），**总步骤数以 Step 0 所选档位为上限**（合并相似操作，不要每个函数调用都单独一步）；条件分支的细节。

#### 3D: `data_flow[]` — 数据流

分析 task 函数之间的数据传递：

- `from` / `to`：数据来源和去向（模块名或函数名）
- `data`：传递的数据描述，上限以 Step 0 所选档位为准（如 "温湿度读数"、"报警状态"）
- `channel`：传输通道
  - `shared_dict` → 通过共享 dict 传递（如 `data["temp"] = ...`）
  - `function_return` → 函数返回值传递
  - `global_var` → 全局变量
  - `queue` → 通过 Queue 传递（async 模式）
  - `callback_param` → 回调函数参数
- `rate`：刷新频率（如 `1Hz`、`on_change`、`100ms`）

**LLM 自主决定：** data_flow 的粒度（可合并同类型流或逐条列出），**总边数以 Step 0 所选档位为上限**（只保留核心数据流，过于细节或单向无分支的流省略）。

#### 3E: `task_registry[]` — 任务注册清单

从 main.py 提取调度器注册信息（timer 模式从 `sc.register()` 提取，async 模式从 `asyncio.create_task()` 提取）：

- `name`：任务名
- `callback`：回调函数名
- `interval_ms`：执行间隔
- `mode`：`periodic` / `once` / `on_event`

#### 3F: `diagnostics` — 诊断信息

LLM 分析代码后填写：

- `total_modules`：architecture 中的模块总数
- `total_dependencies`：depends_on 的依赖边总数
- `max_depth`：依赖图最大深度（从 entry 向下数）
- `circular_deps`：检测到的循环依赖（应为空数组）
- `orphan_modules`：未被任何模块依赖的模块（如纯工具函数）
- `machine_direct_access`：直接 import machine 的模块（除 main.py 外应警告）

### Step 4: 校验 diagram.json

用 `browser_validate` 的 `diagram_mermaid` 校验 diagram.json（schema 不符 → 修改 → 重新校验，直到 pass）。

### Step 5: 渲染 Mermaid .md + SVG + PNG + HTML（联合必需输出）

**这是本 skill 的主要输出。** 用 `browser_validate` 的 `diagram_render` 从 diagram.json 渲染三类图，各输出 .md + SVG + PNG + HTML（`--format all` 等价），用 `file_operation` 写入项目存储 `docs/`：

| 文件 | Mermaid 图类型 | 内容 |
|------|---------------|------|
| `docs/architecture.md` + `.svg` + `.png` + `.html` | `graph TB` | 分层架构图：subgraph 按层分组，节点=模块，边=依赖 |
| `docs/flowchart.md` + `.svg` + `.png` + `.html` | `sequenceDiagram` | 执行流程图：MCU 参与者，按 phase 分组，条件分支 + 错误处理 |
| `docs/data_flow.md` + `.svg` + `.png` + `.html` | `graph LR` | 数据流图：模块间数据通道，不同类型箭头表示不同 channel |

SVG/PNG 渲染与 HTML（Mermaid.js）均由 Blockless `diagram_render` provider 负责（未加载时返回 `partial`）。

### Step 7: 更新 manifest

用 `file_operation` 读取项目存储的 `project-manifest.json`，更新 `diagrams` 段后写回 —— 不使用本地 shell 或 host Python：

```text
file_operation (read project-manifest.json)
设置 diagrams 段：
  json              = docs/diagram.json
  architecture      = docs/architecture.md   architecture_svg/png/html = docs/architecture.{svg,png,html}
  flowchart         = docs/flowchart.md       flowchart_svg/png/html    = docs/flowchart.{svg,png,html}
  data_flow         = docs/data_flow.md       data_flow_svg/png/html    = docs/data_flow.{svg,png,html}
  generated_at      = 当前 UTC ISO-8601 时间戳
file_operation (write project-manifest.json)   # 保留既有键，仅合并 diagrams 段
```

---

## 与其他 skill 的关系

- ← `upy-generate`：输入完整 firmware 代码 + manifest
- 与 `upy-wiring` 并行：可同时生成
- → VS Code 插件 WebView：展示 Mermaid 图（Markdown 预览）或 SVG

---

## 强约束

- **LLM 生成 JSON，脚本只做校验 + 渲染**：与 `upy-generate` 模式一致
- **schema 是唯一契约**：diagram.json 必须通过 `validate_json.py` 校验
- **必须通读所有 firmware/*.py**：不跳过任何文件，架构分析基于真实代码
- **层 ID 必须使用 enum 值**：`board`, `lib`, `driver`, `task`, `entry`, `host`, `test`
- **flow phase 必须使用 enum 值**：`boot`, `init`, `scan`, `create`, `assembly`, `run`, `shutdown`
- **data_flow channel 必须使用 enum 值**：`function_return`, `shared_dict`, `global_var`, `queue`, `callback_param`
- **module.source 必须使用 enum 值**：`scaffold_template`, `llm_generated`, `upypi_download`, `github_download`, `cold_driver`, `user_custom`
- **provides/depends_on 从真实 import 和 def 提取**：不编造符号
- **diagnostics 如实填写**：包括 orphan_modules 和 machine_direct_access 警告
- **渲染脚本防御式读取**：缺失字段不会崩溃，但会在 stderr 输出警告
- **SVG + PNG + HTML 为必需输出**：脚本默认 `--format all`，同时生成 .md、.svg、.png 和 .html；仅 `--format md` 可跳过图片和HTML
- **可读性约束（各档位上限见 Step 0 参数对照表，默认中等。保证 PNG 在 16:9 比例下清晰可读）**：

  | 字段 | 简单 | 中等（默认） | 详细 | 说明 |
  |------|:----:|:--------:|:----:|------|
  | `architecture` 总模块数 | ≤6 | ≤10 | ≤16 | 合并功能相近的模块 |
  | 每层模块数 | ≤2 | ≤4 | ≤6 | 按层拆分上限 |
  | `role` | ≤8 字 | ≤10 字 | ≤14 字 | 节点框第 2 行，过长导致节点膨胀 |
  | `cross_layer_deps[].label` | ≤4 字 | ≤6 字 | ≤10 字 | 边标签嵌在箭头中间，过长使连线拥挤 |
  | `cross_layer_deps[]` 总边数 | ≤6 | ≤12 | ≤20 | 跨层边是拥挤主因，只保留核心依赖 |
  | `flow[].action` | ≤4 字 | ≤6 字 | ≤8 字 | 时序图纵向空间受 16:9 限制 |
  | `flow[].detail` | ≤8 字 | ≤12 字 | ≤16 字 | 在 action 下方折行，过长侵占垂直空间 |
  | `flow[]` 总步数 | ≤5 | ≤8 | ≤14 | 合并相似步骤，不要逐行翻译代码 |
  | `data_flow[].data` | ≤6 字 | ≤8 字 | ≤12 字 | 边标签，过长导致箭头被挤压 |
  | `data_flow[]` 总边数 | ≤2 | ≤4 | ≤8 | 只保留核心数据流 |
  | 16:9 比例 | ≤70% | ≤70% | ≤70% | LLM 预演 Mermaid 渲染，超出即合并 |
