---
name: review-browser
description: Use when reviewing MicroPython code changes against historical maintainer review patterns inside Blockless Web Builder. Provides semantic search across ~19.5K categorized review comments. Triggers when the user wants to review code, find review examples, or get feedback on MicroPython changes/diffs.
---

# review-browser

## Purpose

AI-assisted code review for MicroPython using historical review patterns from the lead maintainer: given a changeset, semantically search a database of ~19.5K categorized review comments to surface relevant examples (with severity + domain) and generate review context. A shared review tool. Blockless Web Builder is the only target runtime for this browser skill.

## Plugin Equivalence

Equivalent source skill:
- `review`

This browser contract preserves the source skill's semantic-search capability, severity/domain categorization, and review workflow. The source-side diff CLI + reviewer command-line/MCP pipeline is replaced by Blockless primitives only:
- `file_operation`
- `browser_validate`
- `phase_complete`

Validation kinds retained for this skill:
- `review_context`
- `review_verify`

## Inputs

- Blockless project id and project store snapshot.
- The changeset to review (the set of modified files / a diff supplied from the project store).

## Outputs

- A review-context artifact: matched historical patterns with a summary table (file paths, severities, domains) and review guidance.
- `phase_complete` (when invoked as a step) with `status`, `evidence`, `artifacts`, and a recoverable `next_action` when needed.

## Blockless Primitive Sequence

1. `file_operation`: read the changeset (modified files / diff) from the project store.
2. `browser_validate` (`review_context`): semantically search the ~19.5K-pattern database for matches to the changeset; return the matched patterns with severity + domain (returns `partial` until the review provider/index is loaded).
3. `browser_validate` (`review_verify`): check the produced findings; `blocking` findings block.
4. The LLM synthesizes the review using the matched patterns as context.
5. `phase_complete`: return the review context and findings.

## Runtime State And Partial Results

- Status is `success`, `partial`, or `failed`.
- Missing runtime state returns a partial envelope such as:

```json
{
  "status": "partial",
  "capability_required": "browser_validate.review_context",
  "next_action": "load_provider"
}
```
- `capability_required` describes a missing Blockless review provider / pattern index, not a browser limitation.

## Failure Conditions

- Return `failed` when `review_verify` reports `blocking` findings, or the changeset is empty/unreadable.
- Return `partial` when the review provider / pattern index is not loaded, or project-store access is missing.
- Include `capability_required` (`browser_validate.<kind>`) and `next_action` (`load_provider`/`sign_in`).
- Do not bypass Blockless primitives for local execution paths.

## Domain Review vs browser_validate (boundary)

`browser_validate` performs the objective subset — semantic pattern search (`review_context`) and findings check (`review_verify`). The LLM synthesizes the actual review narrative from the matched maintainer patterns. The pattern database (~19.5K categorized comments, by severity and domain) is the authority for what good MicroPython review looks like. Blockless Web Builder runs both.

## How it works

1. Provide the changeset (modified files or a diff) from the Blockless project store — `review_context` accepts changesets of any size and chunks multi-file diffs internally for embedding.
2. `review_context` returns the most relevant historical review patterns, each tagged with a severity and a domain (see the taxonomy below).
3. Use the matched patterns as review guidance: for each changed area, surface the patterns that apply, then write concrete, actionable review comments grounded in those precedents.
4. `review_verify` gates the findings; blocking findings must be addressed before the review is considered clean.

The pattern database mirrors the maintainer's historical review focus — prefer its precedents over generic advice when they apply to the changed code.

## Categorization taxonomy

`review_context` tags every matched pattern (and you tag every finding you write) along three axes — the same taxonomy the maintainer's pattern database is categorized by. Use these exact values so findings filter and aggregate consistently.

**Domain** (what the finding is about):
`correctness` (logic bugs, edge cases, error handling) · `code_style` (formatting, naming) · `api_design` (public interfaces, function design) · `memory` (allocation, leaks) · `performance` (speed, efficiency) · `portability` (cross-platform) · `documentation` (comments, clarity) · `testing` (coverage, quality) · `security` (vulnerabilities) · `architecture` (design patterns, structure) · `build_system` (build config) · `error_handling` (error paths, recovery).

**Severity** (how strongly it must be acted on):
`blocking` (must fix before merge) · `suggestion` (recommended improvement) · `nitpick` (minor style/preference).

**Component** (which part of the codebase):
`py_core` (py/) · `extmod` (extmod/) · `port_specific` (ports/) · `drivers` (hardware drivers) · `tools` (build/dev tools) · `tests` (test suite) · `docs` (documentation) · `build_system` (build config).

## Standalone pattern search (no changeset)

Beyond changeset-driven review, the same ~19.5K-pattern index supports **topic search** — finding review examples without supplying a diff (e.g. "what has been said about memory allocation", "examples of GPIO-configuration feedback", "show me the maintainer's style"). Query the index by free text and optionally filter by the taxonomy axes:

- **domain** filter (e.g. `memory`, `correctness`) — one of the 12 domains above.
- **severity** filter — `blocking` / `suggestion` / `nitpick`.
- **component** filter (e.g. `py_core`, `port_specific`) — one of the 8 components above.
- **style-only** filter — return only the comments that exemplify the maintainer's review style.

This is the same semantic search as `review_context`, issued with a topic query instead of a changeset; present the matched comments (with their domain/severity tags) directly and summarize the common themes. Use it when the user asks about a pattern/topic rather than handing you specific code to review.

## Two-step verification

After assembling findings, run `review_verify` to cross-check each against the actual changeset before presenting — this drops false positives from pattern-matching without context.

Format each finding as a structured record:

```json
{
  "file": "extmod/asyncio/stream.py",
  "line": 42,
  "severity": "blocking",
  "domain": "correctness",
  "description": "POLLHUP not handled in ioctl bitmask",
  "diff_hunk": "the relevant diff hunk text"
}
```

`review_verify` returns one verdict per finding:
- **confirmed** — valid; keep (optionally adjust severity).
- **partially_valid** — has merit but needs adjustment; update severity/description.
- **false_positive** — wrong; drop it from the review.
- **inconclusive** — could not be determined; use judgment.

Drop false positives, adjust partially-valid findings, then present the verified set as the final review.

## Data scope

The pattern database holds **~19.5K categorized review comments** from `micropython/micropython` and `micropython/micropython-lib` (2013–2026): PR review comments, issue comments, and review verdicts. It is the authority for what good MicroPython review looks like — cite the actual matched comments when referencing a precedent, and prefer them over generic advice when they apply.
