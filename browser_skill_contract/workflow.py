from __future__ import annotations

from typing import Any

from .runtime import ArtifactStore, BrowserValidateRouter, FakeDeviceAdapter


MAIN_SKILL_CHAIN = [
    "upy-analyze-browser",
    "upy-select-hw-browser",
    "upy-flash-mpy-firmware-browser",
    "upy-scaffold-browser",
    "upy-generate-browser",
    "upy-deploy-browser",
]


def _persist_files(store: ArtifactStore, files: dict[str, str]) -> None:
    for path, content in files.items():
        store.write(path, content)


def _persist_artifacts(store: ArtifactStore, artifacts: list[dict[str, Any]]) -> None:
    for artifact in artifacts:
        content = artifact.get("content", "")
        if not isinstance(content, str):
            import json

            content = json.dumps(content, indent=2, sort_keys=True)
        store.write(artifact["path"], content)


def _stop_if_not_success(result: dict[str, Any]) -> dict[str, Any] | None:
    if result.get("status") == "success":
        return None
    return result


def _phase_result(phase: str, result: dict[str, Any]) -> dict[str, Any]:
    return {"phase": phase, **result}


def _default_pin_plan(manifest: dict[str, Any]) -> list[dict[str, str]]:
    pins = ["GPIO2", "GPIO4", "GPIO5", "GPIO18", "GPIO19"]
    plan = []
    for index, component in enumerate(manifest.get("components", [])):
        mode = "digital_out" if component.get("type") == "digital_output" else "gpio"
        plan.append({"component": component["id"], "pin": pins[index % len(pins)], "mode": mode})
    return plan


def _runtime_files(files: dict[str, str]) -> dict[str, str]:
    host_only_prefixes = ("tests/", "tools/", "docs/", "mocks/")
    return {path: content for path, content in files.items() if not path.startswith(host_only_prefixes)}


def _generate_minimal_firmware(files: dict[str, str], manifest: dict[str, Any]) -> dict[str, str]:
    generated = dict(files)
    pin_lines = [
        "PIN_PLAN = %r" % manifest.get("pin_plan", []),
        "PROJECT_INTENT = %r" % manifest.get("intent", ""),
        "print('running %s')" % manifest.get("project_name", "micropython-project"),
    ]
    generated["firmware/main.py"] = "\n".join(pin_lines) + "\n"
    generated["firmware/conf.py"] = "PROJECT_NAME = %r\n" % manifest.get("project_name", "micropython-project")
    generated.setdefault("firmware/boot.py", "# boot hook\n")
    return generated


def run_main_browser_workflow(
    *,
    request: dict[str, Any],
    artifact_store: ArtifactStore,
    validator: BrowserValidateRouter,
    device: FakeDeviceAdapter,
) -> dict[str, Any]:
    analyze = validator.run("manifest", request)
    _persist_artifacts(artifact_store, analyze.get("artifacts", []))
    if failed := _stop_if_not_success(analyze):
        return _phase_result("analyze", failed)

    manifest = analyze["manifest"]
    analyze_phase = validator.run("manifest_phase", {"phase": "analyze", "manifest": manifest})
    if failed := _stop_if_not_success(analyze_phase):
        return _phase_result("analyze", failed)

    probe = device.run({"action": "probe", "payload": {}})
    if probe.get("status") != "success":
        return _phase_result("select_hw", probe)

    board = probe.get("board", {}) | {"id": probe.get("board", {}).get("id", "esp32-devkit-v1")}
    selected = validator.run(
        "select_hw_manifest",
        {"manifest": manifest, "board": board, "pin_plan": _default_pin_plan(manifest)},
    )
    _persist_artifacts(artifact_store, selected.get("artifacts", []))
    if failed := _stop_if_not_success(selected):
        return _phase_result("select_hw", failed)
    manifest = selected["manifest"]

    select_phase = validator.run("manifest_phase", {"phase": "select_hw", "manifest": manifest})
    if failed := _stop_if_not_success(select_phase):
        return _phase_result("select_hw", failed)

    # Full firmware contract chain: resolve page -> download -> plan -> (approval) -> execute.
    # The real upy-flash-mpy-firmware-browser skill gates flash_execute behind an
    # approval_request (esp32_flash_confirm) and supports firmware_action variants
    # (download_only / already_flashed / ...). This non-interactive smoke run cannot
    # perform a human approval, so it exercises the download_and_flash happy path; a
    # production host must still gate flash_execute on explicit user confirmation.
    firmware_page = validator.run("firmware_page_resolve", {"board": board, "url": board.get("firmware_url", "")})
    if failed := _stop_if_not_success(firmware_page):
        return _phase_result("flash_firmware", failed)

    firmware_download = validator.run(
        "firmware_download",
        {"name": f"{board['id']}-micropython.bin", "bytes": firmware_page.get("firmware_page", {}).get("bytes", 0)},
    )
    if failed := _stop_if_not_success(firmware_download):
        return _phase_result("flash_firmware", failed)

    firmware = validator.run("firmware_flash_plan", {"manifest": manifest, "board": board})
    _persist_artifacts(artifact_store, firmware.get("artifacts", []))
    if failed := _stop_if_not_success(firmware):
        return _phase_result("flash_firmware", failed)

    firmware_execute = validator.run(
        "firmware_flash_execute",
        {"board": board, "firmware": firmware_download.get("firmware", {}), "plan": firmware.get("plan", {})},
    )
    if failed := _stop_if_not_success(firmware_execute):
        return _phase_result("flash_firmware", failed)

    firmware_phase = validator.run("manifest_phase", {"phase": "flash_firmware", "manifest": manifest})
    if failed := _stop_if_not_success(firmware_phase):
        return _phase_result("flash_firmware", failed)

    scaffold = validator.run("scaffold_generate", {"project_name": manifest["project_name"], "manifest": manifest})
    if failed := _stop_if_not_success(scaffold):
        return _phase_result("scaffold", failed)

    files = {**scaffold["files"], **request.get("extra_files", {})}
    _persist_files(artifact_store, files)
    _persist_artifacts(artifact_store, scaffold.get("artifacts", []))

    contract = validator.run("scaffold_contract", {"files": _runtime_files(files), "manifest": manifest})
    if failed := _stop_if_not_success(contract):
        return _phase_result("scaffold", failed)

    package_result = validator.run("package_resolve", {"packages": manifest.get("packages", [])})
    if failed := _stop_if_not_success(package_result):
        return _phase_result("generate", failed)

    upypi_result = validator.run("upypi_resolve", {"packages": manifest.get("packages", [])})
    if failed := _stop_if_not_success(upypi_result):
        return _phase_result("generate", failed)

    files = _generate_minimal_firmware(files, manifest)
    _persist_files(artifact_store, files)

    quality = validator.run("generate_quality", {"files": _runtime_files(files), "manifest": manifest})
    _persist_artifacts(artifact_store, quality.get("artifacts", []))
    if failed := _stop_if_not_success(quality):
        return _phase_result("generate", failed)

    syntax = validator.run("python_syntax", {"files": _runtime_files(files)})
    if failed := _stop_if_not_success(syntax):
        return _phase_result("generate", failed)

    deploy_plan = validator.run("deploy_plan", {"files": files, "manifest": manifest})
    _persist_artifacts(artifact_store, deploy_plan.get("artifacts", []))
    if failed := _stop_if_not_success(deploy_plan):
        return _phase_result("deploy", failed)

    deploy_files = {path: files[path] for path in deploy_plan["deploy_files"] if path in files}
    device_result = device.run({"action": "deploy", "payload": {"files": deploy_files}})
    if device_result.get("status") != "success":
        return _phase_result("deploy", device_result)

    judged = validator.run("deploy_result_judge", {"device_result": device_result})
    if failed := _stop_if_not_success(judged):
        return _phase_result("deploy", failed)

    phase_complete = {
        "status": "success",
        "skill_chain": MAIN_SKILL_CHAIN,
        "artifacts": sorted(artifact_store.snapshot()),
        "deployed_files": device_result["deployed_files"],
    }
    return {
        "status": "success",
        "phase": "deploy",
        "project_name": manifest["project_name"],
        "artifacts": phase_complete["artifacts"],
        "deployed_files": device_result["deployed_files"],
        "phase_complete": phase_complete,
    }


def run_scaffold_deploy_workflow(
    *,
    project_name: str,
    artifact_store: ArtifactStore,
    validator: BrowserValidateRouter,
    device: FakeDeviceAdapter,
) -> dict[str, Any]:
    scaffold = validator.run("scaffold_generate", {"project_name": project_name})
    if failed := _stop_if_not_success(scaffold):
        return failed

    files = scaffold["files"]
    _persist_files(artifact_store, files)
    _persist_artifacts(artifact_store, scaffold.get("artifacts", []))

    contract = validator.run("scaffold_contract", {"files": files})
    if failed := _stop_if_not_success(contract):
        return failed

    syntax = validator.run("python_syntax", {"files": _runtime_files(files)})
    if failed := _stop_if_not_success(syntax):
        return failed

    deploy_plan = validator.run("deploy_plan", {"files": files})
    if failed := _stop_if_not_success(deploy_plan):
        return failed
    _persist_artifacts(artifact_store, deploy_plan.get("artifacts", []))

    deploy_files = {
        path: files[path]
        for path in deploy_plan["deploy_files"]
        if path in files
    }
    device_result = device.run({"action": "deploy", "payload": {"files": deploy_files}})
    if device_result.get("status") != "success":
        return device_result

    judged = validator.run("deploy_result_judge", {"device_result": device_result})
    if failed := _stop_if_not_success(judged):
        return failed

    return {
        "status": "success",
        "project_name": project_name,
        "artifacts": sorted(artifact_store.snapshot()),
        "deployed_files": device_result["deployed_files"],
    }

