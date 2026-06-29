import json
import subprocess
import sys


def run_cli(*args):
    return subprocess.run(
        [sys.executable, "-m", "browser_skill_contract.cli", *args],
        check=True,
        capture_output=True,
        text=True,
    )


def test_cli_catalog_outputs_manifest_summary():
    result = run_cli("catalog")
    payload = json.loads(result.stdout)

    assert "upy-deploy-browser" in payload["browser_skills"]
    assert payload["source_to_browser"]["mpremote-live-session"] == "webserial-live-session-browser"


def test_cli_dry_run_workflow_outputs_phase_result():
    result = run_cli("dry-run-workflow", "--project-name", "blink")
    payload = json.loads(result.stdout)

    assert payload["status"] == "success"
    assert "firmware/main.py" in payload["artifacts"]
