from __future__ import annotations

import ast
from typing import Any, Callable

from .runtime import BrowserValidateRouter, ContractError


HOST_ONLY_PREFIXES = ("tests/", "tools/", "docs/", "mocks/")
MAIN_PHASES = {"analyze", "select_hw", "scaffold", "generate", "deploy"}


def _files(payload: dict[str, Any]) -> dict[str, str]:
    files = payload.get("files", {})
    if not isinstance(files, dict):
        raise ContractError("files must be an object")
    return files


def _ok(**extra: Any) -> dict[str, Any]:
    return {"status": "success", "errors": [], "warnings": [], "artifacts": [], **extra}


def _fail(errors: list[dict[str, Any]], **extra: Any) -> dict[str, Any]:
    return {"status": "failed", "errors": errors, "warnings": [], "artifacts": [], **extra}


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
    if "package_network" not in set(capabilities or []):
        return {
            "status": "partial",
            "capability_required": "browser_validate.package_resolve",
            "errors": [],
            "warnings": ["package resolution requires a host package/network provider"],
            "artifacts": [],
        }
    resolved = [{"name": name, "source": "upypi"} for name in packages]
    return _ok(resolved=resolved)


def resolve_upypi(payload: dict[str, Any], capabilities: set[str] | None = None) -> dict[str, Any]:
    result = resolve_packages(payload, capabilities)
    if result.get("capability_required") == "browser_validate.package_resolve":
        result = {**result, "capability_required": "browser_validate.upypi_resolve"}
    return result


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


def _capability_handler(
    handler: Callable[[dict[str, Any], set[str] | None], dict[str, Any]],
    capabilities: set[str],
) -> Callable[[dict[str, Any]], dict[str, Any]]:
    return lambda payload: handler(payload, capabilities)


def build_default_validation_router(
    advertised_kinds: set[str],
    capabilities: set[str] | None = None,
) -> BrowserValidateRouter:
    router = BrowserValidateRouter(advertised_kinds)
    host_capabilities = set(capabilities or [])
    handlers: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
        "project_files": validate_project_files,
        "manifest": validate_manifest,
        "manifest_phase": validate_manifest_phase,
        "select_hw_manifest": validate_select_hw_manifest,
        "python_syntax": validate_python_syntax,
        "scaffold_generate": generate_scaffold,
        "scaffold_contract": validate_scaffold_contract,
        "generate_quality": validate_generate_quality,
        "package_resolve": _capability_handler(resolve_packages, host_capabilities),
        "upypi_resolve": _capability_handler(resolve_upypi, host_capabilities),
        "deploy_plan": plan_deploy_files,
        "deploy_result_judge": judge_deploy_result,
    }
    for kind, handler in handlers.items():
        router.register(kind, handler)
    return router
