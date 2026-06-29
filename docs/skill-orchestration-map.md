# Skill Orchestration Map

The 27 browser skills mirror the upstream **two-spine, three-tier** structure. The machine-readable
edges live in `browser_skill_manifest.json` (`tier`/`spine`/`phase`/`orchestrates`/`calls` per skill) and are
surfaced by `python -m browser_skill_contract.cli catalog` under `orchestration`. This doc is the human view.

## Tiers

- **orchestrator** — sequences child skills, generates nothing itself (`upy-norm-pkg-browser`,
  `upy-project-browser`, `upy-autofix-browser`).
- **phase** — a main-pipeline stage with a `next_phase` handoff.
- **atomic** — one bounded transformation (the rules-heavy normalization/optimization/generation skills).
- **tool** — a shared capability called by many skills.

## Spine A — project pipeline (一句话造硬件)

Main phase chain (each phase hands off via `phase_complete.next_phase`):

```
upy-analyze-browser → upy-select-hw-browser → upy-flash-mpy-firmware-browser
  → upy-scaffold-browser → upy-generate-browser → upy-deploy-browser
```

Attached to the pipeline:
- `upy-simulate-browser` (phase, 4.5) — optional PC-side simulation after generate.
- `upy-wiring-browser`, `upy-diagram-browser` (atomic) — parallel visuals, non-blocking.
- `upy-gen-driver-browser` (atomic) — exception path when no driver exists; `calls` →
  `upy-norm-driver-browser`, `webserial-device-interaction-browser`.
- `upy-autofix-browser` (orchestrator) — on deploy failure; `orchestrates`/`calls` →
  `upy-generate-browser`, `upy-select-hw-browser`, `upy-analyze-browser` (graded delegation, ≤3 attempts).
- `upy-project-browser` (orchestrator) — end-to-end wrapper; `orchestrates` the analyze→deploy chain;
  `calls` → `fetch-doc-browser`, `upy-pkg-guide-browser`, `upy-autofix-browser`.

Edges: `upy-analyze-browser` → `upy-pkg-guide-browser` → `fetch-doc-browser`;
`upy-deploy-browser` → `webserial-device-interaction-browser` / `-file-transfer-browser` / `-live-session-browser`.

## Spine B — driver normalization (驱动开发规范化)

Orchestrated by `upy-norm-pkg-browser` (6-step chain), which `orchestrates`:

```
upy-norm-driver-browser → (upy-norm-main-browser | upy-gen-main-browser)
  → upy-gen-readme-browser → upy-gen-pkg-browser → upy-pack-driver-browser → upy-deploy-browser
```

Side-chain atomics (user-invoked, not in the orchestrator path):
- `upy-opt-driver-browser` — performance optimization.
- `upy-slim-driver-browser` — memory optimization.

## Shared tools

`upy-pkg-guide-browser` (`calls` → `fetch-doc-browser`), `fetch-doc-browser`, `review-browser`,
`webserial-device-interaction-browser`, `webserial-file-transfer-browser`, `webserial-live-session-browser`.

## Notes

- A skill's domain rules are applied by the LLM; `browser_validate` only performs the objective subset
  (parse / structure / provider-backed fetch / render). See each skill's "domain … vs browser_validate" boundary.
- Execution maps to Blockless primitives only: `file_operation`, `browser_validate`, `device_command`,
  `approval_request`, `phase_complete`. There is no local command execution.
