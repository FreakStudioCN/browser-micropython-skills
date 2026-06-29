---
name: upy-pack-driver-browser
description: Use when packaging a MicroPython driver into the standard GraftSense directory structure inside Blockless Web Builder. Triggers like "打包驱动", "pack driver", "生成驱动包目录", "整理成标准目录", after normalizing/generating all files.
---

# upy-pack-driver-browser

## Purpose

Organize already-generated driver files (`<chip>.py`, `main.py`, `README.md`, `package.json`) into the standard GraftSense package directory structure and emit a `LICENSE`. Generates no content — only arranges files. Blockless Web Builder is the only target runtime for this browser skill.

## Plugin Equivalence

Equivalent source skill:
- `upy-pack-driver`

This browser contract preserves the source skill's responsibility, structure rules, and failure semantics. Source-side local file moves/writes are replaced by Blockless primitives only:
- `file_operation`
- `approval_request`
- `browser_validate`
- `phase_complete`

Validation kinds retained for this skill:
- `project_files`

## Inputs

- Blockless project id and project store snapshot.
- The project-store path of the driver `.py` (with `main.py`, `README.md`, `package.json` already present alongside it).

## Outputs

- The standard `<chip>_driver/` directory tree (`code/`, `package.json`, `README.md`, `LICENSE`) in the project store.
- `phase_complete` for `upy-pack-driver` with `status`, `evidence`, `artifacts`, and a recoverable `next_action` when needed.

## Blockless Primitive Sequence

1. `file_operation`: read the present files; check the required set exists (warn + stop if a file is missing).
2. Arrange the standard tree per the rules below (LLM-driven; see the domain/validate boundary section).
3. `browser_validate` (`project_files`): confirm all arranged paths are project-relative.
4. `approval_request` + `file_operation`: confirm and write the arranged tree + `LICENSE`.
5. `phase_complete`: return status, evidence, and artifacts.

## Runtime State And Partial Results

- `phase_complete.status` is `success`, `partial`, or `failed`.
- Missing runtime state returns a partial envelope such as:

```json
{
  "status": "partial",
  "phase": "upy-pack-driver",
  "capability_required": "browser_validate.project_files",
  "next_action": "load_provider"
}
```
- `capability_required` describes missing Blockless runtime state or provider registration, not a browser limitation.

## Failure Conditions

- Return `failed` when a required input file is missing (prompt to run the matching skill first).
- Return `partial` when a required Blockless provider, project-store access, or user approval is missing.
- Include `capability_required` (`browser_validate.<kind>` / `file_operation.<action>`) and `next_action` (`load_provider`/`sign_in`/`grant_file_access`).
- Do not bypass Blockless primitives for local execution paths.

## Domain Operation vs browser_validate (boundary)

Arrangement is the LLM applying the structure rules below. `browser_validate` performs only the objective subset — are all arranged paths project-relative (`project_files`). It does **not** decide the tree shape; that is the rules' job. Blockless Web Builder runs both.

## 角色定位

你是 GraftSense MicroPython 驱动打包助手。在其他 Skill（`/upy-norm-driver`、`/upy-gen-main`、`/upy-gen-readme`、`/upy-gen-pkg`）已执行完毕后，将同目录下已生成的文件组织成标准驱动包目录结构。

**本 Skill 不生成任何内容，只负责组织文件。**

## 标准目录结构

```
<chip>_driver/
├── code/
│   ├── <chip>.py          ← 驱动文件
│   ├── main.py            ← 测试文件
│   └── <subpkg>/          ← 子包依赖目录（若存在）
│       ├── __init__.py
│       └── ...
├── package.json           ← 包配置文件
├── README.md              ← 说明文档
└── LICENSE                ← MIT 许可证
```

## 执行步骤

1. 读取用户指定的驱动 `.py` 文件
2. 从文件名提取芯片名（去掉 `.py` 后缀即为芯片名，如 `bmp280.py` → `bmp280`）
3. 检查同目录下是否存在以下文件及目录：
   - `main.py`
   - `README.md`
   - `package.json`
   - 含 `__init__.py` 的子目录（子包依赖，若有则列出名称）
   缺失的文件列出 ⚠️ 警告，提示先运行对应 Skill
4. 预览将创建的目录结构（含文件来源说明）
5. 询问用户："确认创建 `<chip>_driver/` 目录并整理文件吗？"
6. 用户确认后执行：
   - 创建 `<chip>_driver/code/` 目录
   - 复制驱动文件 → `<chip>_driver/code/<chip>.py`
   - 复制 `main.py` → `<chip>_driver/code/main.py`
   - **若同目录下存在含 `__init__.py` 的子包目录**：整体复制到 `<chip>_driver/code/<subpkg>/`（保留子目录内所有文件）
   - 复制 `README.md` → `<chip>_driver/README.md`
   - 复制 `package.json` → `<chip>_driver/package.json`
   - 生成 `<chip>_driver/LICENSE`（MIT 固定模板，见下方）
7. 输出最终目录结构确认

## LICENSE 固定模板

```
MIT License

Copyright (c) 2026 leezisheng

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## 输出格式

1. 列出检查结果（各文件是否存在）
2. 预览目录结构
3. 询问用户确认
4. 执行后输出：
   ```
   <chip>_driver/
   ├── code/
   │   ├── <chip>.py        ✓
   │   ├── main.py          ✓
   │   └── <subpkg>/        ✓ (若存在子包)
   ├── package.json         ✓
   ├── README.md            ✓
   └── LICENSE              ✓ (generated)
   ```

## 完整规范参考

本 Skill 的目录结构规则基于 GraftSense 驱动编写规范文档（22 章、2200+ 行），已随本仓库附带，按相对路径查阅：

[docs/reference/upy_driver_dev_spec_summary.md](../docs/reference/upy_driver_dev_spec_summary.md)
