import pytest

from browser_skill_contract.runtime import ContractError, allowed_validate_kinds
from browser_skill_contract.validation import (
    build_default_validation_router,
    plan_deploy_files,
    resolve_packages,
    validate_generate_quality,
    validate_manifest,
    validate_manifest_phase,
    validate_python_syntax,
    validate_select_hw_manifest,
)


def test_python_syntax_reports_success_and_errors():
    ok = validate_python_syntax({"files": {"firmware/main.py": "print('ok')\n"}})
    bad = validate_python_syntax({"files": {"firmware/main.py": "if True print('x')\n"}})

    assert ok == {"status": "success", "errors": [], "warnings": [], "artifacts": []}
    assert bad["status"] == "failed"
    assert bad["errors"][0]["path"] == "firmware/main.py"


def test_deploy_plan_excludes_host_only_files_by_default():
    result = plan_deploy_files(
        {
            "files": {
                "firmware/main.py": "print('deploy')",
                "tests/test_main.py": "",
                "tools/helper.py": "",
                "docs/readme.md": "",
                "mocks/sensor.py": "",
                "lib/driver.py": "",
            }
        }
    )

    assert result["status"] == "success"
    assert result["deploy_files"] == ["firmware/main.py", "lib/driver.py"]
    assert sorted(result["excluded_files"]) == [
        "docs/readme.md",
        "mocks/sensor.py",
        "tests/test_main.py",
        "tools/helper.py",
    ]


def test_default_validation_router_handles_mvp_kinds():
    router = build_default_validation_router(
        {
            "project_files",
            "python_syntax",
            "scaffold_generate",
            "scaffold_contract",
            "deploy_plan",
            "deploy_result_judge",
        }
    )

    scaffold = router.run("scaffold_generate", {"project_name": "blink"})
    contract = router.run("scaffold_contract", {"files": scaffold["files"]})
    deploy = router.run("deploy_plan", {"files": scaffold["files"]})
    judged = router.run("deploy_result_judge", {"device_result": {"status": "success"}})

    assert scaffold["status"] == "success"
    assert "firmware/main.py" in scaffold["files"]
    assert contract["status"] == "success"
    assert deploy["status"] == "success"
    assert judged["status"] == "success"


def test_main_chain_validation_providers_handle_manifest_select_and_generate_quality():
    manifest = validate_manifest(
        {
            "project_name": "blink",
            "intent": "Blink the onboard LED",
            "components": [{"id": "led", "type": "digital_output"}],
        }
    )
    phase = validate_manifest_phase({"phase": "analyze", "manifest": manifest["manifest"]})
    selected = validate_select_hw_manifest(
        {
            "manifest": manifest["manifest"],
            "board": {"id": "esp32-devkit-v1"},
            "pin_plan": [{"component": "led", "pin": "GPIO2", "mode": "digital_out"}],
        }
    )
    quality = validate_generate_quality(
        {
            "files": {
                "firmware/main.py": "print('ok')\n",
                "firmware/boot.py": "# boot\n",
                "firmware/conf.py": "PROJECT_NAME = 'blink'\n",
            }
        }
    )

    assert manifest["status"] == "success"
    assert phase["status"] == "success"
    assert selected["status"] == "success"
    assert quality["status"] == "success"


def test_package_resolve_requires_network_capability_for_dependencies():
    result = resolve_packages({"packages": ["micropython-foo"]}, capabilities=set())

    assert result["status"] == "partial"
    assert result["capability_required"] == "browser_validate.package_resolve"

def test_capabilities_without_reference_mode_raise_loudly():
    with pytest.raises(ContractError):
        build_default_validation_router({"firmware_flash_plan"}, capabilities={"firmware_provider"})


def test_runtime_kind_stays_partial_in_production_even_with_provider_flag():
    # Production path never honors capability flags; a real provider must be
    # registered instead. This guarantees no fabricated success leaks to runtime.
    router = build_default_validation_router({"firmware_flash_plan"})
    result = router.run("firmware_flash_plan", {"board": {"id": "esp32"}})

    assert result["status"] == "partial"
    assert result["capability_required"] == "browser_validate.firmware_flash_plan"


def test_reference_mode_fabricates_success_only_as_explicit_double():
    router = build_default_validation_router(
        {"firmware_flash_plan"},
        capabilities={"firmware_provider"},
        reference_mode=True,
    )
    result = router.run("firmware_flash_plan", {"board": {"id": "esp32"}})

    assert result["status"] == "success"


def test_default_validation_router_registers_every_schema_kind():
    router = build_default_validation_router(allowed_validate_kinds())

    assert set(router._handlers) == allowed_validate_kinds()


def test_runtime_provider_kinds_return_partial_without_loaded_provider_state():
    runtime_kinds = {
        "doc_fetch",
        "package_fetch",
        "package_resolve",
        "upypi_resolve",
        "awesome_micropython_search",
        "doc_extract_pdf",
        "arduino_convert",
        "firmware_page_resolve",
        "firmware_download",
        "firmware_flash_plan",
        "firmware_flash_execute",
        "uf2_manual_confirm",
        "mpy_compile",
    }
    router = build_default_validation_router(runtime_kinds)

    for kind in sorted(runtime_kinds):
        result = router.run(kind, {"packages": ["micropython-foo"], "files": {"firmware/main.py": "print(1)\n"}})
        assert result["status"] == "partial", kind
        assert result["capability_required"] == f"browser_validate.{kind}", kind
        assert result["next_action"] in {
            "load_provider",
            "sign_in",
            "connect_device",
            "grant_usb_permission",
        }


def test_deterministic_provider_kinds_have_success_and_failure_paths():
    files = {"firmware/main.py": "print('ok')\n", "firmware/boot.py": "# boot\n", "firmware/conf.py": "PROJECT_NAME = 'blink'\n"}
    manifest_payload = {
        "project_name": "blink",
        "intent": "Blink LED",
        "components": [{"id": "led", "type": "digital_output"}],
    }
    manifest = validate_manifest(manifest_payload)["manifest"]
    deterministic_cases = {
        "project_files": ({"files": files}, {"files": {"../bad.py": ""}}),
        "manifest": (manifest_payload, {"project_name": "broken", "components": []}),
        "manifest_phase": ({"phase": "analyze", "manifest": manifest}, {"phase": "unknown", "manifest": manifest}),
        "select_hw_manifest": (
            {"manifest": manifest, "board": {"id": "esp32"}, "pin_plan": [{"component": "led", "pin": "GPIO2"}]},
            {"manifest": manifest, "board": {}, "pin_plan": []},
        ),
        "scaffold_generate": ({"project_name": "blink"}, {"project_name": "blink"}),
        "scaffold_contract": ({"files": files}, {"files": {"firmware/main.py": "if True print(1)"}}),
        "deploy_plan": ({"files": files}, {"files": {"docs/readme.md": "host docs"}}),
        "deploy_result_judge": ({"device_result": {"status": "success"}}, {"device_result": {"status": "failed", "stderr": "boom"}}),
        "generate_quality": ({"files": files}, {"files": {"firmware/main.py": ""}}),
        "python_syntax": ({"files": files}, {"files": {"firmware/main.py": "if True print(1)"}}),
        "wiring": ({"manifest": manifest}, {"manifest": {}}),
        "wiring_render": ({"wiring": [{"from": "led", "to": "GPIO2"}]}, {"wiring": []}),
        "diagram_mermaid": ({"manifest": manifest}, {"manifest": {}}),
        "diagram_render": ({"mermaid": "graph TD\nA-->B"}, {"mermaid": ""}),
        "simulate_run": ({"files": files}, {"files": {"firmware/main.py": "raise Exception('x')\n"}}),
        "review_context": ({"files": files}, {"files": {}}),
        "review_verify": ({"findings": []}, {"findings": [{"severity": "high", "message": "bug"}]}),
        "autofix_triage": ({"errors": []}, {"errors": [{"message": "boom"}]}),
        "hardware_sanity": ({"board": {"id": "esp32"}, "pin_plan": [{"pin": "GPIO2"}]}, {"board": {}, "pin_plan": []}),
        "device_test_plan": ({"tests": [{"name": "boot"}]}, {"tests": []}),
    }
    router = build_default_validation_router(set(deterministic_cases))

    for kind, (success_payload, failed_payload) in deterministic_cases.items():
        assert router.run(kind, success_payload)["status"] == "success", kind
        if kind != "scaffold_generate":
            assert router.run(kind, failed_payload)["status"] == "failed", kind



