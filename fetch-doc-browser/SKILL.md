---
name: fetch-doc-browser
description: Use when a URL is provided and key information must be extracted from it inside Blockless Web Builder. Supports GitHub files, upypi pages, images, and general web pages. Triggers like "帮我看一下这个链接", "从这个URL提取信息", "读取这个文档", or any URL pasted with a question about its content.
---

# fetch-doc-browser

## Purpose

Given any URL, fetch its content via the Blockless document/package provider and extract the key information (GitHub files, upypi package pages, images, general web pages). Fetching is performed via Blockless primitives; the LLM extracts and summarizes. Blockless Web Builder is the only target runtime for this browser skill.

## Plugin Equivalence

Equivalent source skill:
- `fetch-doc`

This browser contract preserves the source skill's URL-type handling and extraction rules. The source-side fetch script / HTTP CLI is replaced by Blockless primitives only:
- `browser_validate`
- `file_operation`
- `phase_complete`

Validation kinds retained for this skill:
- `doc_fetch`
- `package_fetch`

## Inputs

- The URL to fetch (GitHub blob/raw, upypi page, image, or web page).
- Document/package fetch results returned by the loaded Blockless provider.

## Outputs

- The extracted key information (summary / API table / package fields), and any downloaded artifact written to the project store.
- `phase_complete` (when invoked as a step) with `status`, `evidence`, and a recoverable `next_action` when needed.

## Blockless Primitive Sequence

1. `browser_validate` (`doc_fetch` / `package_fetch`): fetch the URL content (GitHub blob auto-converted to raw; returns `partial` until the provider is loaded).
2. `file_operation`: persist any downloaded image/artifact into the project store.
3. Extract the key information per the rules below (LLM-driven).
4. `phase_complete`: return the extracted result.

## Runtime State And Partial Results

- Status is `success`, `partial`, or `failed`.
- Missing runtime state returns a partial envelope such as:

```json
{
  "status": "partial",
  "capability_required": "browser_validate.doc_fetch",
  "next_action": "load_provider"
}
```
- `capability_required` describes a missing Blockless document/network provider, not a browser limitation.

## Failure Conditions

- Return `failed` when the URL is unreachable or returns no usable content.
- Return `partial` when the document/package provider is not loaded.
- Include `capability_required` (`browser_validate.<kind>`) and `next_action` (`load_provider`/`sign_in`).
- Do not bypass Blockless primitives for local execution paths.

## 执行步骤

### 第一步：识别 URL 类型

| URL 特征 | 处理方式 |
|---|---|
| `github.com/.../blob/...` | 自动转换为 raw URL，脚本获取 |
| `raw.githubusercontent.com/...` | 直接用脚本获取 |
| `upypi.net/pkgs/...` | `browser_validate` 的 `package_fetch` 获取 JSON |
| 图片（.png/.jpg/.gif） | `doc_fetch` 下载到项目存储 |
| 其他网页 | `doc_fetch` 获取 HTML，提取正文 |

### 第二步：获取内容

用 `browser_validate` 的 `doc_fetch`（GitHub blob 自动转 raw；provider 未加载时返回 `partial`）获取内容；图片/产物用 `file_operation` 写入项目存储。

### 第三步：提取关键信息

根据内容类型提取：

| 内容类型 | 提取重点 |
|---|---|
| README.md | 简介、功能列表、快速开始代码、注意事项 |
| 驱动 .py | 类名、构造参数、公共 API 表格 |
| package.json | 包名、版本、依赖、文件列表 |
| 普通文档 | 标题结构、核心段落、代码块 |

### 第四步：输出

以用户问题为导向输出，不固定格式。若用户只是"看一下"，输出摘要；若用户问具体问题，直接回答。
