from browser_skill_contract.runtime import ArtifactStore, FakeDeviceAdapter
from browser_skill_contract.validation import build_default_validation_router
from browser_skill_contract.workflow import run_main_browser_workflow


def _validator(extra_capabilities=None):
    kinds = {
        "manifest",
        "manifest_phase",
        "select_hw_manifest",
        "scaffold_generate",
        "scaffold_contract",
        "generate_quality",
        "python_syntax",
        "package_resolve",
        "upypi_resolve",
        "deploy_plan",
        "deploy_result_judge",
    }
    return build_default_validation_router(kinds, capabilities=set(extra_capabilities or []))


def test_main_browser_workflow_runs_analyze_select_scaffold_generate_deploy_happy_path():
    store = ArtifactStore()
    device = FakeDeviceAdapter({"scan", "probe", "deploy"})

    result = run_main_browser_workflow(
        request={
            "project_name": "blink",
            "intent": "Blink the onboard LED",
            "components": [{"id": "led", "type": "digital_output"}],
        },
        artifact_store=store,
        validator=_validator(),
        device=device,
    )

    assert result["status"] == "success"
    assert result["phase"] == "deploy"
    assert result["phase_complete"]["status"] == "success"
    assert result["phase_complete"]["skill_chain"] == [
        "upy-analyze-browser",
        "upy-select-hw-browser",
        "upy-scaffold-browser",
        "upy-generate-browser",
        "upy-deploy-browser",
    ]
    assert "artifacts/analyze-manifest.json" in store.snapshot()
    assert "artifacts/select-hw-manifest.json" in store.snapshot()
    assert "artifacts/generate-quality.json" in store.snapshot()
    assert sorted(device.files) == ["firmware/boot.py", "firmware/conf.py", "firmware/main.py"]


def test_main_browser_workflow_returns_partial_without_device_probe_capability():
    result = run_main_browser_workflow(
        request={
            "project_name": "blink",
            "intent": "Blink the onboard LED",
            "components": [{"id": "led", "type": "digital_output"}],
        },
        artifact_store=ArtifactStore(),
        validator=_validator(),
        device=FakeDeviceAdapter({"scan", "deploy"}),
    )

    assert result["status"] == "partial"
    assert result["phase"] == "select_hw"
    assert result["capability_required"] == "device_command.probe"


def test_main_browser_workflow_returns_partial_without_package_network_capability():
    result = run_main_browser_workflow(
        request={
            "project_name": "sensor",
            "intent": "Read an external sensor",
            "components": [{"id": "sensor", "type": "i2c_sensor"}],
            "packages": ["micropython-foo"],
        },
        artifact_store=ArtifactStore(),
        validator=_validator(),
        device=FakeDeviceAdapter({"scan", "probe", "deploy"}),
    )

    assert result["status"] == "partial"
    assert result["phase"] == "generate"
    assert result["capability_required"] == "browser_validate.package_resolve"


def test_main_browser_workflow_fails_invalid_manifest():
    result = run_main_browser_workflow(
        request={"project_name": "broken", "components": []},
        artifact_store=ArtifactStore(),
        validator=_validator(),
        device=FakeDeviceAdapter({"scan", "probe", "deploy"}),
    )

    assert result["status"] == "failed"
    assert result["phase"] == "analyze"
    assert result["errors"][0]["field"] == "intent"


def test_main_browser_workflow_deploy_excludes_host_only_files():
    store = ArtifactStore()
    device = FakeDeviceAdapter({"scan", "probe", "deploy"})

    result = run_main_browser_workflow(
        request={
            "project_name": "blink",
            "intent": "Blink the onboard LED",
            "components": [{"id": "led", "type": "digital_output"}],
            "extra_files": {
                "docs/readme.md": "host docs",
                "tests/test_main.py": "host tests",
                "tools/helper.py": "host tools",
                "mocks/sensor.py": "host mocks",
            },
        },
        artifact_store=store,
        validator=_validator(),
        device=device,
    )

    assert result["status"] == "success"
    assert "docs/readme.md" in store.snapshot()
    assert sorted(device.files) == ["firmware/boot.py", "firmware/conf.py", "firmware/main.py"]
