from browser_skill_contract.runtime import ArtifactStore, FakeDeviceAdapter
from browser_skill_contract.validation import build_default_validation_router
from browser_skill_contract.workflow import run_scaffold_deploy_workflow


def test_scaffold_deploy_workflow_writes_artifacts_and_deploys_when_capable():
    store = ArtifactStore()
    validate = build_default_validation_router(
        {"scaffold_generate", "scaffold_contract", "python_syntax", "deploy_plan", "deploy_result_judge"}
    )
    device = FakeDeviceAdapter({"deploy"})

    result = run_scaffold_deploy_workflow(
        project_name="blink",
        artifact_store=store,
        validator=validate,
        device=device,
    )

    assert result["status"] == "success"
    assert "firmware/main.py" in store.snapshot()
    assert "artifacts/deploy-plan.json" in store.snapshot()
    assert sorted(device.files) == ["firmware/boot.py", "firmware/conf.py", "firmware/main.py"]


def test_scaffold_deploy_workflow_returns_partial_without_device_capability():
    store = ArtifactStore()
    validate = build_default_validation_router(
        {"scaffold_generate", "scaffold_contract", "python_syntax", "deploy_plan", "deploy_result_judge"}
    )
    device = FakeDeviceAdapter({"scan"})

    result = run_scaffold_deploy_workflow(
        project_name="blink",
        artifact_store=store,
        validator=validate,
        device=device,
    )

    assert result["status"] == "partial"
    assert result["capability_required"] == "device_command.deploy"
    assert "firmware/main.py" in store.snapshot()
