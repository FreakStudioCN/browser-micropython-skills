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
