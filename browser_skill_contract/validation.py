from __future__ import annotations

import ast
from typing import Any, Callable

from .runtime import BrowserValidateRouter, ContractError


HOST_ONLY_PREFIXES = ("tests/", "tools/", "docs/", "mocks/")
MAIN_PHASES = {"analyze", "select_hw", "flash_firmware", "scaffold", "generate", "deploy"}


def _files(payload: dict[str, Any]) -> dict[str, str]:
    files = payload.get("files", {})
    if not isinstance(files, dict):
        raise ContractError("files must be an object")
    return files


def _ok(**extra: Any) -> dict[str, Any]:
    return {"status": "success", "errors": [], "warnings": [], "artifacts": [], **extra}


def _fail(errors: list[dict[str, Any]], **extra: Any) -> dict[str, Any]:
    return {"status": "failed", "errors": errors, "warnings": [], "artifacts": [], **extra}


def _partial(kind: str, next_action: str = "load_provider", warning: str | None = None) -> dict[str, Any]:
    warnings = [warning] if warning else []
    return {
        "status": "partial",
        "capability_required": f"browser_validate.{kind}",
        "next_action": next_action,
        "errors": [],
        "warnings": warnings,
        "artifacts": [],
    }


def _has_capability(capabilities: set[str] | None, *names: str) -> bool:
    available = set(capabilities or [])
    return bool(available.intersection(names))


def validate_project_files(payload: dict[str, Any]) -> dict[str, Any]:
    files = _files(payload)
    errors = []
    for path, content in files.items():
        if path.startswith("/") or ".." in path.split("/"):
            errors.append({"path": path, "message": "path must be project-relative"})
        if not isinstance(content, str):
            errors.append({"path": path, "message": "content must be text"})
    return _fail(errors) if errors else _ok()


def validate_python_syntax(payload: dict[str, Any]) -> dict[str, Any]:
    errors = []
    for path, content in _files(payload).items():
        if not path.endswith(".py"):
            continue
        try:
            ast.parse(content, filename=path)
        except SyntaxError as exc:
            errors.append(
                {
                    "path": path,
                    "line": exc.lineno,
                    "column": exc.offset,
                    "message": exc.msg,
                }
            )
    return _fail(errors) if errors else _ok()


def validate_manifest(payload: dict[str, Any]) -> dict[str, Any]:
    errors = []
    project_name = payload.get("project_name") or "micropython-project"
    intent = payload.get("intent")
    components = payload.get("components")
    packages = payload.get("packages", [])

    if not isinstance(project_name, str) or not project_name.strip():
        errors.append({"field": "project_name", "message": "project_name must be text"})
    if not isinstance(intent, str) or not intent.strip():
        errors.append({"field": "intent", "message": "intent is required"})
    if not isinstance(components, list) or not components:
        errors.append({"field": "components", "message": "at least one component is required"})
    elif any(not isinstance(item, dict) or not item.get("id") for item in components):
        errors.append({"field": "components", "message": "each component needs an id"})
    if not isinstance(packages, list) or any(not isinstance(item, str) for item in packages):
        errors.append({"field": "packages", "message": "packages must be a list of strings"})

    if errors:
        return _fail(errors)

    manifest = {
        "project_name": project_name.strip(),
        "intent": intent.strip(),
        "components": components,
        "packages": packages,
    }
    return _ok(
        manifest=manifest,
        artifacts=[{"path": "artifacts/analyze-manifest.json", "content": manifest}],
    )


def validate_manifest_phase(payload: dict[str, Any]) -> dict[str, Any]:
    phase = payload.get("phase")
    manifest = payload.get("manifest")
    errors = []
    if phase not in MAIN_PHASES:
        errors.append({"field": "phase", "message": "unknown workflow phase"})
    if not isinstance(manifest, dict):
        errors.append({"field": "manifest", "message": "manifest must be an object"})
    else:
        manifest_result = validate_manifest(manifest)
        errors.extend(manifest_result.get("errors", []))
    return _fail(errors) if errors else _ok(phase=phase)


def validate_select_hw_manifest(payload: dict[str, Any]) -> dict[str, Any]:
    manifest = payload.get("manifest")
    board = payload.get("board")
    pin_plan = payload.get("pin_plan")
    errors = []

    if not isinstance(manifest, dict):
        errors.append({"field": "manifest", "message": "manifest must be an object"})
    if not isinstance(board, dict) or not board.get("id"):
        errors.append({"field": "board", "message": "board.id is required"})
    if not isinstance(pin_plan, list) or not pin_plan:
        errors.append({"field": "pin_plan", "message": "pin_plan is required"})

    component_ids = {item.get("id") for item in manifest.get("components", [])} if isinstance(manifest, dict) else set()
    if isinstance(pin_plan, list):
        for index, item in enumerate(pin_plan):
            if not isinstance(item, dict) or not item.get("component") or not item.get("pin"):
                errors.append({"field": f"pin_plan[{index}]", "message": "component and pin are required"})
                continue
            if component_ids and item["component"] not in component_ids:
                errors.append({"field": f"pin_plan[{index}].component", "message": "component not in manifest"})

    if errors:
        return _fail(errors)

    selected = {**manifest, "board": board, "pin_plan": pin_plan}
    return _ok(
        manifest=selected,
        artifacts=[{"path": "artifacts/select-hw-manifest.json", "content": selected}],
    )


def generate_scaffold(payload: dict[str, Any]) -> dict[str, Any]:
    project_name = payload.get("project_name", "micropython-project")
    files = {
        "firmware/boot.py": "# boot hook\n",
        "firmware/main.py": "print('hello from %s')\n" % project_name,
        "firmware/conf.py": "PROJECT_NAME = %r\n" % project_name,
        "lib/README.md": "Place reusable MicroPython modules here.\n",
    }
    return _ok(files=files, artifacts=[{"path": path, "content": content} for path, content in files.items()])


def validate_scaffold_contract(payload: dict[str, Any]) -> dict[str, Any]:
    files = _files(payload)
    required = {"firmware/main.py", "firmware/boot.py", "firmware/conf.py"}
    missing = sorted(required - set(files))
    errors = [{"path": path, "message": "required scaffold file missing"} for path in missing]
    syntax = validate_python_syntax({"files": files})
    errors.extend(syntax["errors"])
    return _fail(errors) if errors else _ok(warnings=syntax["warnings"])


def validate_generate_quality(payload: dict[str, Any]) -> dict[str, Any]:
    files = _files(payload)
    errors = []
    for path in ["firmware/main.py", "firmware/boot.py", "firmware/conf.py"]:
        if path not in files:
            errors.append({"path": path, "message": "required generated file missing"})
    if not files.get("firmware/main.py", "").strip():
        errors.append({"path": "firmware/main.py", "message": "main.py must not be empty"})
    syntax = validate_python_syntax({"files": files})
    errors.extend(syntax["errors"])
    if errors:
        return _fail(errors)
    artifact = {
        "checked_files": sorted(path for path in files if path.endswith(".py")),
        "checks": ["required_files", "python_syntax"],
    }
    return _ok(artifacts=[{"path": "artifacts/generate-quality.json", "content": artifact}])


def resolve_packages(payload: dict[str, Any], capabilities: set[str] | None = None) -> dict[str, Any]:
    packages = payload.get("packages", [])
    if not isinstance(packages, list) or any(not isinstance(item, str) for item in packages):
        return _fail([{"field": "packages", "message": "packages must be a list of strings"}])
    if not packages:
        return _ok(resolved=[])
    if not _has_capability(capabilities, "package_network", "package_provider", "network_provider", "browser_validate.package_resolve"):
        return _partial("package_resolve", "load_provider", "package resolution requires a Blockless package provider")
    resolved = [{"name": name, "source": "upypi"} for name in packages]
    return _ok(resolved=resolved)


def resolve_upypi(payload: dict[str, Any], capabilities: set[str] | None = None) -> dict[str, Any]:
    packages = payload.get("packages", [])
    if not isinstance(packages, list) or any(not isinstance(item, str) for item in packages):
        return _fail([{"field": "packages", "message": "packages must be a list of strings"}])
    if not packages:
        return _ok(resolved=[])
    if not _has_capability(capabilities, "package_network", "package_provider", "network_provider", "browser_validate.upypi_resolve"):
        return _partial("upypi_resolve", "load_provider", "upypi resolution requires a Blockless package provider")
    return _ok(resolved=[{"name": name, "source": "upypi"} for name in packages])


def plan_deploy_files(payload: dict[str, Any]) -> dict[str, Any]:
    files = _files(payload)
    deploy_files = []
    excluded_files = []
    for path in sorted(files):
        if path.startswith(HOST_ONLY_PREFIXES):
            excluded_files.append(path)
            continue
        if path.endswith(".py"):
            deploy_files.append(path)
    if not deploy_files:
        return _fail([{"field": "files", "message": "no deployable MicroPython files found"}])
    return _ok(
        deploy_files=deploy_files,
        excluded_files=excluded_files,
        artifacts=[
            {
                "path": "artifacts/deploy-plan.json",
                "content": {
                    "deploy_files": deploy_files,
                    "excluded_files": excluded_files,
                },
            }
        ],
    )


def judge_deploy_result(payload: dict[str, Any]) -> dict[str, Any]:
    device_result = payload.get("device_result", {})
    if not isinstance(device_result, dict):
        raise ContractError("device_result must be an object")
    status = device_result.get("status")
    if status == "success":
        return _ok()
    return _fail([{"message": device_result.get("stderr") or "device command failed"}])


def validate_wiring(payload: dict[str, Any]) -> dict[str, Any]:
    manifest = payload.get("manifest")
    if not isinstance(manifest, dict) or not manifest.get("components"):
        return _fail([{"field": "manifest.components", "message": "components are required for wiring"}])
    pin_plan = manifest.get("pin_plan") or [
        {"component": component["id"], "pin": "TBD", "mode": component.get("type", "gpio")}
        for component in manifest.get("components", [])
    ]
    wiring = [{"from": item["component"], "to": item["pin"], "mode": item.get("mode", "gpio")} for item in pin_plan]
    return _ok(wiring=wiring, artifacts=[{"path": "artifacts/wiring.json", "content": wiring}])


def render_wiring(payload: dict[str, Any]) -> dict[str, Any]:
    wiring = payload.get("wiring")
    if not isinstance(wiring, list) or not wiring:
        return _fail([{"field": "wiring", "message": "wiring entries are required"}])
    text = "\n".join(f"{item.get('from')} -> {item.get('to')}" for item in wiring)
    return _ok(rendered=text, artifacts=[{"path": "artifacts/wiring.txt", "content": text}])


def render_diagram_mermaid(payload: dict[str, Any]) -> dict[str, Any]:
    manifest = payload.get("manifest")
    if not isinstance(manifest, dict) or not manifest.get("components"):
        return _fail([{"field": "manifest.components", "message": "components are required for diagram"}])
    lines = ["graph TD", "board[MicroPython board]"]
    for component in manifest.get("components", []):
        lines.append(f"board --> {component['id']}[{component['id']}]")
    mermaid = "\n".join(lines)
    return _ok(mermaid=mermaid, artifacts=[{"path": "artifacts/diagram.mmd", "content": mermaid}])


def render_diagram(payload: dict[str, Any]) -> dict[str, Any]:
    mermaid = payload.get("mermaid")
    if not isinstance(mermaid, str) or not mermaid.strip():
        return _fail([{"field": "mermaid", "message": "diagram source is required"}])
    rendered = {"format": "mermaid", "source": mermaid}
    return _ok(rendered=rendered, artifacts=[{"path": "artifacts/diagram-render.json", "content": rendered}])


def run_simulation(payload: dict[str, Any]) -> dict[str, Any]:
    syntax = validate_python_syntax(payload)
    if syntax["status"] != "success":
        return syntax
    main = _files(payload).get("firmware/main.py", "")
    if "raise Exception" in main or "raise RuntimeError" in main:
        return _fail([{"path": "firmware/main.py", "message": "simulation raised an exception"}])
    return _ok(stdout="simulated run complete", artifacts=[{"path": "artifacts/simulate-run.json", "content": {"stdout": "simulated run complete"}}])


def build_review_context(payload: dict[str, Any]) -> dict[str, Any]:
    files = _files(payload)
    if not files:
        return _fail([{"field": "files", "message": "review requires project files"}])
    context = {"files": sorted(files), "python_files": sorted(path for path in files if path.endswith(".py"))}
    return _ok(context=context, artifacts=[{"path": "artifacts/review-context.json", "content": context}])


def verify_review(payload: dict[str, Any]) -> dict[str, Any]:
    findings = payload.get("findings", [])
    if not isinstance(findings, list):
        return _fail([{"field": "findings", "message": "findings must be a list"}])
    blocking = [item for item in findings if item.get("severity") in {"high", "critical"}]
    if blocking:
        return _fail(blocking)
    return _ok(findings=findings)


def triage_autofix(payload: dict[str, Any]) -> dict[str, Any]:
    errors = payload.get("errors", [])
    if not isinstance(errors, list):
        return _fail([{"field": "errors", "message": "errors must be a list"}])
    if errors:
        return _fail(errors, triage={"action": "manual_review"})
    return _ok(triage={"action": "no_fix_needed"})


def validate_hardware_sanity(payload: dict[str, Any]) -> dict[str, Any]:
    board = payload.get("board")
    pin_plan = payload.get("pin_plan")
    errors = []
    if not isinstance(board, dict) or not board.get("id"):
        errors.append({"field": "board.id", "message": "board id is required"})
    if not isinstance(pin_plan, list) or not pin_plan:
        errors.append({"field": "pin_plan", "message": "pin plan is required"})
    return _fail(errors) if errors else _ok()


def validate_device_test_plan(payload: dict[str, Any]) -> dict[str, Any]:
    tests = payload.get("tests")
    if not isinstance(tests, list) or not tests:
        return _fail([{"field": "tests", "message": "at least one device test is required"}])
    if any(not isinstance(item, dict) or not item.get("name") for item in tests):
        return _fail([{"field": "tests", "message": "each device test needs a name"}])
    return _ok(tests=tests)


def runtime_doc_fetch(payload: dict[str, Any], capabilities: set[str] | None = None) -> dict[str, Any]:
    if not _has_capability(capabilities, "doc_provider", "network_provider", "browser_validate.doc_fetch"):
        return _partial("doc_fetch", "load_provider", "document fetch requires a Blockless document provider")
    return _ok(documents=[{"url": payload.get("url", "about:blank"), "content": payload.get("content", "")}])


def runtime_package_fetch(payload: dict[str, Any], capabilities: set[str] | None = None) -> dict[str, Any]:
    if not _has_capability(capabilities, "package_provider", "network_provider", "browser_validate.package_fetch"):
        return _partial("package_fetch", "load_provider", "package fetch requires a Blockless package provider")
    return _ok(packages=payload.get("packages", []))


def runtime_awesome_search(payload: dict[str, Any], capabilities: set[str] | None = None) -> dict[str, Any]:
    if not _has_capability(capabilities, "package_provider", "network_provider", "browser_validate.awesome_micropython_search"):
        return _partial("awesome_micropython_search", "load_provider", "search requires a Blockless network provider")
    return _ok(results=[])


def runtime_pdf_extract(payload: dict[str, Any], capabilities: set[str] | None = None) -> dict[str, Any]:
    if not _has_capability(capabilities, "pdf_provider", "browser_validate.doc_extract_pdf"):
        return _partial("doc_extract_pdf", "load_provider", "PDF extraction requires a Blockless document provider")
    return _ok(text=payload.get("text", ""))


def runtime_arduino_convert(payload: dict[str, Any], capabilities: set[str] | None = None) -> dict[str, Any]:
    if not _has_capability(capabilities, "arduino_provider", "browser_validate.arduino_convert"):
        return _partial("arduino_convert", "load_provider", "Arduino conversion requires a Blockless conversion provider")
    return _ok(files={"firmware/main.py": payload.get("code", "# converted\n")})


def runtime_firmware_page(payload: dict[str, Any], capabilities: set[str] | None = None) -> dict[str, Any]:
    if not _has_capability(capabilities, "firmware_provider", "network_provider", "browser_validate.firmware_page_resolve"):
        return _partial("firmware_page_resolve", "load_provider", "firmware page lookup requires a Blockless firmware provider")
    return _ok(firmware_page={"board": payload.get("board", {}).get("id", "unknown"), "url": payload.get("url", "")})


def runtime_firmware_download(payload: dict[str, Any], capabilities: set[str] | None = None) -> dict[str, Any]:
    if not _has_capability(capabilities, "firmware_provider", "network_provider", "browser_validate.firmware_download"):
        return _partial("firmware_download", "load_provider", "firmware download requires a Blockless firmware provider")
    return _ok(firmware={"name": payload.get("name", "micropython.bin"), "bytes": payload.get("bytes", 0)})


def runtime_firmware_flash_plan(payload: dict[str, Any], capabilities: set[str] | None = None) -> dict[str, Any]:
    if not _has_capability(capabilities, "firmware_provider", "browser_validate.firmware_flash_plan"):
        return _partial("firmware_flash_plan", "connect_device", "firmware planning requires Blockless firmware/device state")
    plan = {
        "board": payload.get("board", {}).get("id", "unknown"),
        "method": payload.get("method", "webserial"),
        "ready": True,
    }
    return _ok(plan=plan, artifacts=[{"path": "artifacts/firmware-flash-plan.json", "content": plan}])


def runtime_firmware_flash_execute(payload: dict[str, Any], capabilities: set[str] | None = None) -> dict[str, Any]:
    if not _has_capability(capabilities, "firmware_provider", "usb_permission", "browser_validate.firmware_flash_execute"):
        return _partial("firmware_flash_execute", "grant_usb_permission", "firmware flashing requires USB permission")
    return _ok(result={"flashed": True})


def runtime_uf2_manual_confirm(payload: dict[str, Any], capabilities: set[str] | None = None) -> dict[str, Any]:
    if not _has_capability(capabilities, "firmware_provider", "file_picker", "browser_validate.uf2_manual_confirm"):
        return _partial("uf2_manual_confirm", "grant_usb_permission", "UF2 confirmation requires user file/device permission")
    return _ok(confirmed=True)


def runtime_mpy_compile(payload: dict[str, Any], capabilities: set[str] | None = None) -> dict[str, Any]:
    if not _has_capability(capabilities, "compile_provider", "wasm_provider", "browser_validate.mpy_compile"):
        return _partial("mpy_compile", "load_provider", "MPY compilation requires a Blockless compiler provider")
    return _ok(compiled=[])


def _capability_handler(
    handler: Callable[[dict[str, Any], set[str] | None], dict[str, Any]],
    capabilities: set[str],
) -> Callable[[dict[str, Any]], dict[str, Any]]:
    return lambda payload: handler(payload, capabilities)


def build_default_validation_router(
    advertised_kinds: set[str],
    capabilities: set[str] | None = None,
    *,
    reference_mode: bool = False,
) -> BrowserValidateRouter:
    router = BrowserValidateRouter(advertised_kinds)
    requested_capabilities = set(capabilities or [])
    # Fail-fast guard: the reference handlers fabricate deterministic success for
    # runtime-backed kinds (firmware, network, USB, WASM, login). That is a test
    # double, never a real provider. Honoring a capability flag outside an explicit
    # reference run would silently return fake success without doing the work, so
    # refuse it loudly. Production hosts must register a real provider via
    # router.register(); until then runtime-backed kinds stay `partial`.
    if requested_capabilities and not reference_mode:
        raise ContractError(
            "capabilities are honored only in reference_mode (tests/dry-run); "
            "production must register a real provider via router.register() instead "
            "of relying on fabricated reference success"
        )
    host_capabilities = requested_capabilities if reference_mode else set()
    handlers: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
        "project_files": validate_project_files,
        "manifest": validate_manifest,
        "manifest_phase": validate_manifest_phase,
        "select_hw_manifest": validate_select_hw_manifest,
        "scaffold_generate": generate_scaffold,
        "scaffold_contract": validate_scaffold_contract,
        "deploy_plan": plan_deploy_files,
        "deploy_result_judge": judge_deploy_result,
        "generate_quality": validate_generate_quality,
        "python_syntax": validate_python_syntax,
        "wiring": validate_wiring,
        "wiring_render": render_wiring,
        "diagram_mermaid": render_diagram_mermaid,
        "diagram_render": render_diagram,
        "simulate_run": run_simulation,
        "review_context": build_review_context,
        "review_verify": verify_review,
        "autofix_triage": triage_autofix,
        "hardware_sanity": validate_hardware_sanity,
        "device_test_plan": validate_device_test_plan,
        "doc_fetch": _capability_handler(runtime_doc_fetch, host_capabilities),
        "package_fetch": _capability_handler(runtime_package_fetch, host_capabilities),
        "package_resolve": _capability_handler(resolve_packages, host_capabilities),
        "upypi_resolve": _capability_handler(resolve_upypi, host_capabilities),
        "awesome_micropython_search": _capability_handler(runtime_awesome_search, host_capabilities),
        "doc_extract_pdf": _capability_handler(runtime_pdf_extract, host_capabilities),
        "arduino_convert": _capability_handler(runtime_arduino_convert, host_capabilities),
        "firmware_page_resolve": _capability_handler(runtime_firmware_page, host_capabilities),
        "firmware_download": _capability_handler(runtime_firmware_download, host_capabilities),
        "firmware_flash_plan": _capability_handler(runtime_firmware_flash_plan, host_capabilities),
        "firmware_flash_execute": _capability_handler(runtime_firmware_flash_execute, host_capabilities),
        "uf2_manual_confirm": _capability_handler(runtime_uf2_manual_confirm, host_capabilities),
        "mpy_compile": _capability_handler(runtime_mpy_compile, host_capabilities),
    }
    for kind, handler in handlers.items():
        router.register(kind, handler)
    return router
