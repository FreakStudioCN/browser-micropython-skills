import pytest

from browser_skill_contract.runtime import (
    ArtifactStore,
    BrowserValidateRouter,
    CapabilityBroker,
    ContractError,
    FakeDeviceAdapter,
    load_manifest,
    validate_device_command,
    validate_tool_envelope,
)


def test_load_manifest_indexes_browser_skills():
    catalog = load_manifest()

    assert "upy-deploy-browser" in catalog.browser_skills
    assert catalog.source_to_browser["mpremote-file-transfer"] == "webserial-file-transfer-browser"
    assert catalog.validate_kinds_for("upy-generate-browser") >= {
        "generate_quality",
        "python_syntax",
        "mpy_compile",
    }


def test_tool_envelope_rejects_unknown_primitive():
    with pytest.raises(ContractError, match="unknown tool"):
        validate_tool_envelope({"tool": "script_run", "payload": {}})


def test_device_command_schema_rejects_unknown_action():
    with pytest.raises(ContractError, match="unknown device action"):
        validate_device_command({"action": "shell", "payload": {}})


def test_capability_broker_reports_missing_action():
    broker = CapabilityBroker(
        {
            "device_command": ["scan", "probe"],
            "browser_validate": ["python_syntax"],
            "artifact_store": ["read", "write"],
        }
    )

    result = broker.require_device_action("deploy")

    assert result == {
        "status": "partial",
        "capability_required": "device_command.deploy",
    }


def test_artifact_store_uses_project_relative_paths():
    store = ArtifactStore()

    store.write("firmware/main.py", "print('ok')\n")

    assert store.read("firmware/main.py") == "print('ok')\n"
    assert store.list("firmware") == ["firmware/main.py"]

    with pytest.raises(ContractError, match="project-relative"):
        store.write("../escape.py", "")


def test_validate_router_requires_declared_kind():
    router = BrowserValidateRouter({"python_syntax"})

    router.register("python_syntax", lambda payload: {"status": "success", "errors": []})

    assert router.run("python_syntax", {"files": []})["status"] == "success"
    assert router.run("mpy_compile", {}) == {
        "status": "partial",
        "capability_required": "browser_validate.mpy_compile",
    }

    with pytest.raises(ContractError, match="undeclared validation kind"):
        router.run("not_in_schema", {})


def test_fake_device_adapter_is_capability_gated():
    adapter = FakeDeviceAdapter({"scan", "probe", "exec", "cp", "cp_from", "ls"})

    assert adapter.run({"action": "scan"})["status"] == "success"
    assert adapter.run({"action": "exec", "payload": {"code": "print(1)"}})["stdout"] == "print(1)"

    adapter.run({"action": "cp", "payload": {"path": "/main.py", "content": "print('x')"}})

    assert adapter.run({"action": "cp_from", "payload": {"path": "/main.py"}})["content"] == "print('x')"
    assert adapter.run({"action": "hard_reset"}) == {
        "status": "partial",
        "action": "hard_reset",
        "capability_required": "device_command.hard_reset",
    }
