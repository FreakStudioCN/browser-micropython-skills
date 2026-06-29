---
name: upy-deploy-browser
description: Phase 5 — one-shot flash & run. Uploads firmware/ to the board, soft resets, captures output over a persistent device session, reads device-side logs, and makes an initial pass/fail judgment inside Blockless Web Builder. Runs after upy-generate-browser completes.
---

# upy-deploy-browser

## Purpose

Given the generate-phase manifest, upload `firmware/` to the MicroPython board through the Blockless device binding, run it, capture output, and make an initial PASS/FAIL judgment. It does **not** fix errors (that is `upy-autofix-browser`'s job). Blockless Web Builder is the only target runtime for this browser skill.

## Plugin Equivalence

Equivalent source skills:
- `upy-deploy`
- `upy-deploy-plugin`
- `upy-deploy-test`

This browser contract preserves the source skill's phase responsibility, operational rules, required evidence, artifacts, and failure semantics. Source-side device CLI, file transfer, cross-compile, and persistent-session actions are replaced by Blockless primitives only:
- `approval_request`
- `device_command`
- `file_operation`
- `browser_validate`
- `phase_complete`

Validation kinds retained for this phase:
- `deploy_plan`
- `deploy_result_judge`
- `device_test_plan`
- `project_files`

## Inputs

- Blockless project id, project store snapshot, and the generate-phase manifest (`phase: generate`) with the full `firmware/` tree.
- A user-granted Blockless device session (board binding) for board I/O.
- Validation inputs for: `deploy_plan`, `deploy_result_judge`, `device_test_plan`, `project_files`.

## Outputs

- artifacts/deploy-plan.json (upload set + ordering + excluded host-only files).
- Captured REPL output, device-side log files pulled back to the project store, and a structured judgment result.
- `phase_complete` for `deploy` with `status`, `evidence`, `artifacts`, `next_phase`, and a recoverable `next_action` when needed.

## Blockless Primitive Sequence

1. `file_operation`: read the generate manifest, the `firmware/` tree, and `conf.py` (for `LOG_DIR`).
2. `browser_validate` (`deploy_plan`): compute the deployable file set and upload ordering, excluding host-only files.
3. `browser_validate` (`mpy_compile`): cross-compile the deployable `.py` (except `main.py`/`boot.py`) to `.mpy` (returns `partial` until a compile provider is loaded).
4. `approval_request`: confirm flashing to the bound board before mutating device state.
5. `device_command`: upload files (dependencies first, `main.py` last), verify the device file tree, soft reset, wait for reconnect, open a persistent session, and capture output.
6. `device_command` + `file_operation`: pull device-side `run_*.log` files back into the project store.
7. `browser_validate` (`deploy_result_judge`): judge the device result against the failure-signature rules below.
8. `phase_complete`: return status, evidence, artifacts, and routing (`upy-autofix-browser` on FAIL).

## Runtime State And Partial Results

- `phase_complete.status` is `success`, `partial`, or `failed`.
- `phase_complete.evidence` names the device results, captured output, log files, and user approvals used by the phase.
- `phase_complete.next_phase` is `upy-autofix-browser` on FAIL, or `complete` on PASS.
- Missing runtime state returns a partial envelope such as:

```json
{
  "status": "partial",
  "phase": "deploy",
  "capability_required": "device_command.deploy",
  "next_action": "connect_device"
}
```
- `capability_required` describes missing Blockless device/runtime state (no connected board, no USB permission), not a browser limitation.

## Failure Conditions

- Return `failed` when the upload is incomplete, the device result reports a blocking error, or the judgment rules below trip.
- Return `partial` when the Blockless device session, USB permission, connected board, compile provider, or user approval is missing.
- Include `capability_required` with the missing primitive path, for example `device_command.<action>` or `browser_validate.<kind>`.
- Include `next_action` as `connect_device`, `grant_usb_permission`, `load_provider`, or `sign_in` for recoverable runtime gaps.
- Do not bypass Blockless primitives for local execution paths.

## Domain Operation vs browser_validate (boundary)

Device upload/run/capture are performed via the Blockless `device_command` binding; `browser_validate` performs only the objective subset — plan the deploy set (`deploy_plan`), judge the result (`deploy_result_judge`), cross-compile (`mpy_compile`). The PASS/FAIL rules below are local rules applied to captured output and device logs; they do not call any server AI. Blockless Web Builder runs the device operations and the validation together.

## 角色定位

给定 `project-manifest.json`（phase: generate），将 `firmware/` 通过 Blockless 设备绑定上传到 MicroPython 设备、运行、采集输出、初判结果。**不做错误修复（那是 upy-autofix-browser 的职责）。**

## 核心设计

### main.py 的 3 秒启动延时

upy-generate Phase 5 约束 #0 要求 main.py 第一行代码是 `time.sleep(3)`。这给了 deploy 软复位后足够的重连时间：

```
device_command: soft_reset
  → 设备重启，连接断开
  → 主机重新枚举设备（1~3s）
  → device_command 重连 + resume
  → main.py 恰好在 3s 延时窗口内，此时连上不会丢任何输出
```

没有这个延时，设备会话连上时 main.py 可能已经跑了一半（日志头、I2C 扫描结果丢失）。

### print() + 轮转日志双通道

deploy 从两个来源获取设备输出：

| 来源 | 方式 | 特点 |
|------|------|------|
| REPL 实时输出 | `device_command` 持久会话 | `print()` 即时可见，但会话断开即丢失 |
| 设备端日志文件 | `device_command` 读取 `:/log/run_*.log` | 跨重启保留，会话断开仍可读取 |

deploy Phase 5 抓取日志文件作为补充——即使持久会话因断连遗漏了部分输出，日志文件能补全。

## 执行步骤

### Phase 1: 规划与上传文件

先用 `browser_validate` `deploy_plan` 计算可部署文件集与上传顺序（排除 `tests/`、`tools/`、`docs/`、`mocks/` 等 host-only 文件）。再用 `browser_validate` `mpy_compile` 把除 `main.py`/`boot.py` 外的 `.py` 交叉编译为 `.mpy`（provider 未加载时返回 `partial`）。经 `approval_request` 确认后，用 `device_command` 上传。

**上传顺序**：`lib/` → `drivers/` → 配置（board.py / conf.py / boot.py）→ `tasks/` → `main.py`（最后）。先传依赖，后传入口；`main.py` 一旦存在，设备启动即执行，所以排在最后。

每个 `device_command` 文件写入使用 `resume` 语义，避免传输前软复位损坏中间文件。

### Phase 2: 校验文件完整性

用 `device_command` 列出设备文件树（`fs tree` / 逐目录 `fs ls`），与本地 `deploy_plan` 文件列表对比，缺文件则重传。

### Phase 3: 软复位 + 等待重连

用 `device_command` 软复位（不带 resume —— 就是要让设备重启），然后轮询等待设备就绪（`wait_for_device`，超时 60s）：

```
每 2 秒:
  device_command: resume exec "print(1)"
  → 成功（收到 "1"）: 设备就绪，main.py 正在 3s 延时窗口内
  → 失败（连接错误/无应答）: 继续等待
  → 超时 60s: 报 FAIL，终止
```

**注意**：软复位后设备重启，主机可能换端口标识。如果重连持续失败，重新扫描设备列表（`device_command` scan）。

### Phase 4: 持久会话 + 采集输出

设备自动运行 main.py。用 `device_command` 建立持久会话捕获完整输出（60s 超时）。

**超时策略**：
- 看到 `"starting scheduler"` 或等效标志 → 提前判定 PASS，结束采集
- 60s 无关键标志但无错误 → PASS（可能只是没有打印标志）
- 输出 Traceback → FAIL

持久会话由 Blockless 设备绑定提供（等价于 webserial-live-session-browser 的能力），跨平台差异由设备绑定层吸收。

### Phase 5: 抓取设备端日志

持久会话可能因断连丢失部分输出。用 `file_operation` 读取 `firmware/conf.py` 的 `LOG_DIR`（默认 `/log`），然后用 `device_command` 从设备文件系统读取并下载日志：

- **即时分析**：`device_command` 读取（`fs cat`）`:/log/run_*.log` 内容，结构化为日志报告（P0~P2 分级 + MemoryError/ENOMEM 检测），输出 `deploy_log_report.json`。
- **下载原始文件**：`device_command` 下载（`fs cp`）每个 `run_*.log` 到项目存储 `deploy_logs/`，FAIL 时随上下文传给 `upy-autofix-browser`。

日志文件包含从 boot 到 crash 的完整记录（即使会话断开也保留），是判断失败原因的关键数据源。

### Phase 6: 初判

**纯本地规则，不调服务端 AI。** 用 `browser_validate` `deploy_result_judge` 结合两个数据源判定：

**数据源 1 — REPL 实时输出（signature 规则）：**

```
判定规则:
  output 含 "Traceback (most recent call last)" → FAIL (Python 异常)
  output 含 "rst cause:"                          → FAIL (硬件复位)
  output 含 "Guru Meditation Error"               → FAIL (ESP32 内核 panic)
  output 含 "MemoryError" / "ENOMEM"              → FAIL (内存不足)
  60s 内无任何输出                                  → FAIL (设备无响应)
  其他                                            → PASS ✓
```

**数据源 2 — `deploy_log_report.json`：** 若 `error_count > 0` 且 REPL 规则未命中 → 仍判定 FAIL（日志中有错误，但 REPL 输出可能因断连丢失）。P0/P1 级别直接 FAIL，P2 级别作为辅助信息。

```
输出结构:
  { status: "PASS" | "FAIL",
    output: <采集的完整 REPL 输出>,
    log_report: <deploy_log_report.json 内容>,
    log_files: <deploy_logs/ 目录下的原始 .log 文件列表>,
    deployed_files: <设备文件树>,
    device_info: { firmware, flash_free, freq } }
```

PASS → 流程结束，展示运行结果。
FAIL → 将完整上下文（REPL 输出 + deploy_log_report.json + deploy_logs/*.log）随 `phase_complete(next_phase="upy-autofix-browser")` 传给 autofix。

## 平台差异

端口标识、持久会话方式、端口变化处理在本地版本中按 Windows/macOS/Linux 区分。在 Blockless Web Builder 中，这些由设备绑定层统一吸收：用户授权设备会话后，`device_command` 提供跨平台一致的 scan / connect / exec / fs / reset / stream 动作；端口变化由设备绑定层在重连时处理。

## 与 webserial-* skill 的关系

| 步骤 | 对应能力（device_command） | 备用 skill |
|------|---------------------------|-----------|
| 上传文件 | `fs cp`（递归 + main.py 排最后） | webserial-file-transfer-browser |
| 校验文件 | `fs tree` / `fs ls` 对比 | webserial-device-interaction-browser |
| 软复位 | `soft_reset`（不用 resume） | webserial-device-interaction-browser |
| 重连等待 | `resume exec "print(1)"` 轮询 | webserial-device-interaction-browser |
| 持久会话 | 持久 session 采集完整 REPL 输出 | webserial-live-session-browser |
| 抓日志 | `fs cat` 读内容 + `fs cp` 下载原始 .log | webserial-file-transfer-browser |

## 与其他 skill 的关系

- ← `upy-generate-browser`：输入完整 firmware/ + manifest（phase: generate）
- → `upy-autofix-browser`：FAIL 时传入错误上下文
- → `upy-wiring-browser` / `upy-diagram-browser`：并行生成可视化（不阻塞 deploy）

## 强约束

- **不调服务端 AI**：deploy 纯本地判定，快速闭环。错误分析留给 autofix
- **不修改代码**：只上传、运行、判定。修复是 autofix 的职责
- **上传前必须 cross-compile**：除 main.py 和 boot.py 外，所有 .py 必须先经 `browser_validate` `mpy_compile` 编译为 .mpy 再上传。减小 Flash 占用，避免设备端 import 时内存不足
- **main.py / boot.py 必须保留 .py**：MicroPython 启动只认 .py 入口文件，编译为 .mpy 后无法自动执行
- **main.py 必须最后上传**：它触发设备启动主逻辑，先传依赖再传入口
- **文件写入必须带 resume 语义**：不带 resume 的写入会先软复位，传输中间文件损坏
- **重连超时 60s**：覆盖设备重枚举 + main.py 3s 延时 + 启动初始化
- **日志双源采集**：持久会话 REPL 输出 + 设备端轮转日志文件，互补
