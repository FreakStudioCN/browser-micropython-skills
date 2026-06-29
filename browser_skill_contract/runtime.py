from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, Callable


ROOT = PurePosixPath(__file__).parent.parent


class ContractError(ValueError):
    """Raised when a browser skill contract payload is invalid."""


@dataclass(frozen=True)
class SkillCatalog:
    manifest: dict[str, Any]
    browser_skills: set[str]
    source_to_browser: dict[str, str]
    browser_to_validate_kinds: dict[str, set[str]]
    orchestration: dict[str, dict[str, Any]]

    def validate_kinds_for(self, browser_skill: str) -> set[str]:
        return set(self.browser_to_validate_kinds.get(browser_skill, set()))

    def orchestration_for(self, browser_skill: str) -> dict[str, Any]:
        return dict(self.orchestration.get(browser_skill, {}))


def _repo_path(*parts: str):
    from pathlib import Path

    return Path(__file__).resolve().parents[1].joinpath(*parts)


def _load_json(path: str) -> dict[str, Any]:
    return json.loads(_repo_path(path).read_text(encoding="utf-8"))


def load_manifest(path: str = "browser_skill_manifest.json") -> SkillCatalog:
    manifest = _load_json(path)
    browser_skills: set[str] = set()
    source_to_browser: dict[str, str] = {}
    browser_to_validate_kinds: dict[str, set[str]] = {}
    orchestration: dict[str, dict[str, Any]] = {}

    for entry in manifest.get("skills", []):
        browser_skill = entry["browser_skill"]
        browser_skills.add(browser_skill)
        browser_to_validate_kinds[browser_skill] = set(entry.get("browser_validate_kinds", []))
        orchestration[browser_skill] = {
            "tier": entry.get("tier"),
            "spine": entry.get("spine"),
            "phase": entry.get("phase"),
            "orchestrates": list(entry.get("orchestrates", [])),
            "calls": list(entry.get("calls", [])),
        }
        for source in entry.get("source_skills", []):
            if source in source_to_browser:
                raise ContractError(f"duplicate source skill mapping: {source}")
            source_to_browser[source] = browser_skill

    return SkillCatalog(
        manifest=manifest,
        browser_skills=browser_skills,
        source_to_browser=source_to_browser,
        browser_to_validate_kinds=browser_to_validate_kinds,
        orchestration=orchestration,
    )


def _enum_from_schema(path: str, *keys: str) -> set[str]:
    node: Any = _load_json(path)
    for key in keys:
        node = node[key]
    return set(node["enum"])


def allowed_tools() -> set[str]:
    return _enum_from_schema("contracts/browser_tools.schema.json", "properties", "tool")


def allowed_device_actions() -> set[str]:
    return _enum_from_schema("contracts/device_command.schema.json", "properties", "action")


def allowed_validate_kinds() -> set[str]:
    return _enum_from_schema("contracts/browser_validate.schema.json", "$defs", "kind")


def validate_tool_envelope(envelope: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(envelope, dict):
        raise ContractError("tool envelope must be an object")
    if set(envelope) - {"tool", "payload"}:
        raise ContractError("tool envelope has unknown fields")
    if "tool" not in envelope:
        raise ContractError("tool envelope missing tool")
    if envelope["tool"] not in allowed_tools():
        raise ContractError(f"unknown tool: {envelope['tool']}")
    if not isinstance(envelope.get("payload"), dict):
        raise ContractError("tool envelope payload must be an object")
    return envelope


def validate_device_command(command: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(command, dict):
        raise ContractError("device command must be an object")
    if "action" not in command:
        raise ContractError("device command missing action")
    if command["action"] not in allowed_device_actions():
        raise ContractError(f"unknown device action: {command['action']}")
    if "payload" in command and not isinstance(command["payload"], dict):
        raise ContractError("device command payload must be an object")
    return command


def validate_browser_validate_request(request: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(request, dict):
        raise ContractError("browser_validate request must be an object")
    if "kind" not in request:
        raise ContractError("browser_validate request missing kind")
    if request["kind"] not in allowed_validate_kinds():
        raise ContractError(f"undeclared validation kind: {request['kind']}")
    if not isinstance(request.get("input"), dict):
        raise ContractError("browser_validate input must be an object")
    return request


class CapabilityBroker:
    def __init__(self, capabilities: dict[str, Any]):
        self.capabilities = capabilities

    def has_device_action(self, action: str) -> bool:
        return action in set(self.capabilities.get("device_command", []))

    def has_validation_kind(self, kind: str) -> bool:
        return kind in set(self.capabilities.get("browser_validate", []))

    def require_device_action(self, action: str) -> dict[str, str] | None:
        validate_device_command({"action": action})
        if self.has_device_action(action):
            return None
        return {
            "status": "partial",
            "capability_required": f"device_command.{action}",
        }

    def require_validation_kind(self, kind: str) -> dict[str, str] | None:
        if kind not in allowed_validate_kinds():
            raise ContractError(f"undeclared validation kind: {kind}")
        if self.has_validation_kind(kind):
            return None
        return {
            "status": "partial",
            "capability_required": f"browser_validate.{kind}",
        }


class ArtifactStore:
    def __init__(self):
        self._files: dict[str, str] = {}

    def _normalize(self, path: str) -> str:
        if not path or path.startswith("/"):
            raise ContractError("path must be project-relative")
        normalized = PurePosixPath(path)
        if any(part in {"", ".", ".."} for part in normalized.parts):
            raise ContractError("path must be project-relative")
        return normalized.as_posix()

    def write(self, path: str, content: str) -> dict[str, str]:
        normalized = self._normalize(path)
        self._files[normalized] = content
        return {"status": "success", "path": normalized}

    def read(self, path: str) -> str:
        normalized = self._normalize(path)
        if normalized not in self._files:
            raise ContractError(f"artifact not found: {normalized}")
        return self._files[normalized]

    def list(self, prefix: str = "") -> list[str]:
        if prefix:
            normalized = self._normalize(prefix).rstrip("/") + "/"
            return sorted(path for path in self._files if path.startswith(normalized))
        return sorted(self._files)

    def delete(self, path: str) -> dict[str, str]:
        normalized = self._normalize(path)
        removed = [key for key in self._files if key == normalized or key.startswith(normalized + "/")]
        for key in removed:
            del self._files[key]
        return {"status": "success", "path": normalized}

    def snapshot(self) -> dict[str, str]:
        return dict(sorted(self._files.items()))


class BrowserValidateRouter:
    def __init__(self, advertised_kinds: set[str]):
        undeclared = advertised_kinds - allowed_validate_kinds()
        if undeclared:
            raise ContractError(f"undeclared validation kind: {sorted(undeclared)[0]}")
        self.advertised_kinds = set(advertised_kinds)
        self._handlers: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {}

    def register(self, kind: str, handler: Callable[[dict[str, Any]], dict[str, Any]]) -> None:
        if kind not in allowed_validate_kinds():
            raise ContractError(f"undeclared validation kind: {kind}")
        self._handlers[kind] = handler

    def run(self, kind: str, payload: dict[str, Any]) -> dict[str, Any]:
        if kind not in allowed_validate_kinds():
            raise ContractError(f"undeclared validation kind: {kind}")
        if kind not in self.advertised_kinds:
            return {
                "status": "partial",
                "capability_required": f"browser_validate.{kind}",
            }
        if kind not in self._handlers:
            return {
                "status": "partial",
                "capability_required": f"browser_validate.{kind}",
            }
        result = self._handlers[kind](payload)
        if "status" not in result:
            raise ContractError("validation handler result missing status")
        return result


class FakeDeviceAdapter:
    def __init__(self, advertised_actions: set[str]):
        undeclared = advertised_actions - allowed_device_actions()
        if undeclared:
            raise ContractError(f"unknown device action: {sorted(undeclared)[0]}")
        self.advertised_actions = set(advertised_actions)
        self.files: dict[str, str] = {}

    def run(self, command: dict[str, Any]) -> dict[str, Any]:
        validate_device_command(command)
        action = command["action"]
        if action not in self.advertised_actions:
            return {
                "status": "partial",
                "action": action,
                "capability_required": f"device_command.{action}",
            }

        payload = command.get("payload", {})
        if action == "scan":
            return {"status": "success", "action": action, "ports": [{"id": "fake-webserial"}]}
        if action == "probe":
            return {"status": "success", "action": action, "board": {"sysname": "micropython"}}
        if action == "exec":
            return {"status": "success", "action": action, "stdout": payload.get("code", ""), "stderr": ""}
        if action == "cp":
            path = payload["path"]
            self.files[path] = payload.get("content", "")
            return {"status": "success", "action": action, "path": path}
        if action == "cp_from":
            path = payload["path"]
            return {"status": "success", "action": action, "path": path, "content": self.files[path]}
        if action == "deploy":
            for path, content in payload.get("files", {}).items():
                self.files[path] = content
            return {
                "status": "success",
                "action": action,
                "deployed_files": sorted(payload.get("files", {})),
            }
        if action == "ls":
            return {"status": "success", "action": action, "files": sorted(self.files)}

        return {"status": "success", "action": action}

