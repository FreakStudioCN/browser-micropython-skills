# Plugin Capability Crosswalk

Blockless Web Builder is the only target runtime for this repository. The upstream and plugin skill directories remain reference material for phase intent and expected evidence; browser skills execute through Blockless primitives.

| Source capability | Blockless browser replacement |
| --- | --- |
| `script_run:init_manifest.py` | `browser_validate:manifest` plus `file_operation` writes to `artifacts/analyze-manifest.json` |
| `script_run:select_hw_manifest.py` | `browser_validate:select_hw_manifest` plus `file_operation` writes to `artifacts/select-hw-manifest.json` |
| `script_run:init_scaffold.py` | `browser_validate:scaffold_generate` and `browser_validate:scaffold_contract` |
| local lint/check quality gates | `browser_validate:generate_quality`, `browser_validate:python_syntax`, and `browser_validate:mpy_compile` |
| package and documentation fetch helpers | `browser_validate:package_fetch`, `browser_validate:package_resolve`, `browser_validate:upypi_resolve`, `browser_validate:doc_fetch`, and `browser_validate:awesome_micropython_search` |
| PDF extraction and Arduino conversion helpers | `browser_validate:doc_extract_pdf` and `browser_validate:arduino_convert` |
| firmware page, download, and flash helpers | `browser_validate:firmware_page_resolve`, `browser_validate:firmware_download`, `browser_validate:firmware_flash_plan`, `browser_validate:firmware_flash_execute`, and `browser_validate:uf2_manual_confirm` |
| `mpremote` deploy, run, REPL, and file transfer behavior | `device_command:deploy`, `device_command:exec`, `device_command:stream`, `device_command:cp`, and `device_command:cp_from` through Blockless WebSerial/WebUSB binding |
| review and autofix scripts | `browser_validate:review_context`, `browser_validate:review_verify`, `browser_validate:autofix_triage`, and `browser_validate:hardware_sanity` |
| wiring, diagram, and simulation scripts | `browser_validate:wiring`, `browser_validate:wiring_render`, `browser_validate:diagram_mermaid`, `browser_validate:diagram_render`, and `browser_validate:simulate_run` |
| phase result files | `phase_complete` plus `file_operation` artifacts in the Blockless project store |

`capability_required` means the current Blockless runtime is missing state or a provider: login, network-backed registry access, WASM validation, USB permission, a connected device, or a user approval. It is not a claim that a browser runtime lacks the ability.

ViperIDE is an implementation reference for browser serial and device techniques only. It is not a runtime target for this repository.
