import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_manifest():
    return json.loads((ROOT / "browser_skill_manifest.json").read_text(encoding="utf-8"))


def upstream_skill_names():
    names = set()
    for skill_file in ROOT.glob("*/SKILL.md"):
        name = skill_file.parent.name
        if not name.endswith("-browser"):
            names.add(name)
    return names


def browser_skill_names(manifest):
    return {entry["browser_skill"] for entry in manifest["skills"]}


def test_contract_files_exist():
    required = [
        "browser_skill_manifest.json",
        "contracts/browser_tools.schema.json",
        "contracts/device_command.schema.json",
        "contracts/browser_validate.schema.json",
        "contracts/capability_matrix.md",
        "adapters/blockless-device-binding.md",
        "adapters/validation-adapter.md",
        "adapters/artifact-store-adapter.md",
        "docs/blockless-consuming-browser-skill-contract.md",
    ]

    missing = [path for path in required if not (ROOT / path).exists()]

    assert missing == []


def test_every_upstream_skill_has_browser_mapping():
    manifest = load_manifest()
    mapped_sources = {source for entry in manifest["skills"] for source in entry["source_skills"]}

    missing = sorted(upstream_skill_names() - mapped_sources)

    assert missing == []


def test_manifest_only_uses_browser_primitives():
    manifest = load_manifest()
    allowed = {
        "approval_request",
        "file_operation",
        "device_command",
        "browser_validate",
        "phase_complete",
    }

    unknown = {
        primitive
        for entry in manifest["skills"]
        for primitive in entry["primitives"]
        if primitive not in allowed
    }

    assert unknown == set()


def test_declared_browser_skills_have_skill_md():
    manifest = load_manifest()
    missing = [
        skill
        for skill in sorted(browser_skill_names(manifest))
        if not (ROOT / skill / "SKILL.md").exists()
    ]

    assert missing == []


def test_browser_validate_kinds_are_declared_in_schema():
    manifest = load_manifest()
    schema = json.loads(
        (ROOT / "contracts/browser_validate.schema.json").read_text(encoding="utf-8")
    )
    declared = set(schema["$defs"]["kind"]["enum"])
    referenced = {
        kind
        for entry in manifest["skills"]
        for kind in entry.get("browser_validate_kinds", [])
    }

    assert sorted(referenced - declared) == []


def test_browser_skill_docs_do_not_expose_local_commands_as_actions():
    forbidden = [
        "script_run",
        "mpremote ",
        "curl ",
        "git ",
        "esptool",
        "flake8",
        "pylint",
        "mpy-cross",
    ]
    offenders = []

    for skill_file in sorted(ROOT.glob("*-browser/SKILL.md")):
        text = skill_file.read_text(encoding="utf-8").lower()
        for token in forbidden:
            if token in text:
                offenders.append(f"{skill_file.relative_to(ROOT)}: {token.strip()}")

    assert offenders == []

def test_blockless_docs_do_not_present_viperide_as_runtime_target():
    checked = [
        ROOT / "README.md",
        ROOT / "adapters" / "blockless-device-binding.md",
        ROOT / "adapters" / "validation-adapter.md",
        ROOT / "adapters" / "artifact-store-adapter.md",
        ROOT / "docs" / "blockless-consuming-browser-skill-contract.md",
    ]
    offenders = []

    for path in checked:
        text = path.read_text(encoding="utf-8").lower()
        for phrase in ["viperide adapter", "viperide device adapter", "runtime target for this skill repository"]:
            if phrase in text and "not a runtime target" not in text:
                offenders.append(f"{path.relative_to(ROOT)}: {phrase}")

    assert offenders == []
