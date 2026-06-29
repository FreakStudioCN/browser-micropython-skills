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
3. `browser_validate` (`review_verify`): check the produced findings; high/critical findings block.
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

- Return `failed` when `review_verify` reports blocking (high/critical) findings, or the changeset is empty/unreadable.
- Return `partial` when the review provider / pattern index is not loaded, or project-store access is missing.
- Include `capability_required` (`browser_validate.<kind>`) and `next_action` (`load_provider`/`sign_in`).
- Do not bypass Blockless primitives for local execution paths.

## Domain Review vs browser_validate (boundary)

`browser_validate` performs the objective subset — semantic pattern search (`review_context`) and findings check (`review_verify`). The LLM synthesizes the actual review narrative from the matched maintainer patterns. The pattern database (~19.5K categorized comments, by severity and domain) is the authority for what good MicroPython review looks like. Blockless Web Builder runs both.

## How it works

1. Provide the changeset (modified files or a diff) from the Blockless project store — `review_context` accepts changesets of any size and chunks multi-file diffs internally for embedding.
2. `review_context` returns the most relevant historical review patterns, each tagged with severity (e.g. blocking / non-blocking) and domain (e.g. memory, ISR, API design, style).
3. Use the matched patterns as review guidance: for each changed area, surface the patterns that apply, then write concrete, actionable review comments grounded in those precedents.
4. `review_verify` gates the findings; high/critical findings must be addressed before the review is considered clean.

The pattern database mirrors the maintainer's historical review focus — prefer its precedents over generic advice when they apply to the changed code.
