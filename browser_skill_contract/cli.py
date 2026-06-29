from __future__ import annotations

import argparse
import json

from .runtime import ArtifactStore, FakeDeviceAdapter, load_manifest
from .validation import build_default_validation_router
from .workflow import run_main_browser_workflow


def _print_json(payload: dict) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def command_catalog() -> None:
    catalog = load_manifest()
    _print_json(
        {
            "browser_skills": sorted(catalog.browser_skills),
            "source_to_browser": dict(sorted(catalog.source_to_browser.items())),
            "validate_kinds": {
                skill: sorted(kinds)
                for skill, kinds in sorted(catalog.browser_to_validate_kinds.items())
            },
            "orchestration": dict(sorted(catalog.orchestration.items())),
        }
    )


def command_dry_run_workflow(project_name: str) -> None:
    store = ArtifactStore()
    validator = build_default_validation_router(
        {
            "manifest",
            "manifest_phase",
            "select_hw_manifest",
            "firmware_page_resolve",
            "firmware_download",
            "firmware_flash_plan",
            "firmware_flash_execute",
            "scaffold_generate",
            "scaffold_contract",
            "python_syntax",
            "generate_quality",
            "package_resolve",
            "upypi_resolve",
            "deploy_plan",
            "deploy_result_judge",
        },
        capabilities={"firmware_provider"},
        reference_mode=True,
    )
    device = FakeDeviceAdapter({"scan", "probe", "deploy"})
    result = run_main_browser_workflow(
        request={
            "project_name": project_name,
            "intent": "Blink the onboard LED",
            "components": [{"id": "led", "type": "digital_output"}],
        },
        artifact_store=store,
        validator=validator,
        device=device,
    )
    _print_json(result)


def main() -> None:
    parser = argparse.ArgumentParser(prog="browser-skill-contract")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("catalog")
    workflow = subparsers.add_parser("dry-run-workflow")
    workflow.add_argument("--project-name", default="micropython-project")
    args = parser.parse_args()

    if args.command == "catalog":
        command_catalog()
    elif args.command == "dry-run-workflow":
        command_dry_run_workflow(args.project_name)


if __name__ == "__main__":
    main()
