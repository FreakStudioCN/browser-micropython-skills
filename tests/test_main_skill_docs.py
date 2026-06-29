from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAIN_CHAIN = [
    "upy-analyze-browser",
    "upy-select-hw-browser",
    "upy-scaffold-browser",
    "upy-generate-browser",
    "upy-deploy-browser",
]


def test_main_chain_skill_docs_declare_contract_sections():
    missing = []

    for skill in MAIN_CHAIN:
        text = (ROOT / skill / "SKILL.md").read_text(encoding="utf-8").lower()
        for heading in [
            "## inputs",
            "## outputs",
            "## primitive sequence",
            "## failure and partial conditions",
        ]:
            if heading not in text:
                missing.append(f"{skill}: {heading}")

    assert missing == []


def test_main_chain_skill_docs_do_not_expose_local_commands_as_actions():
    forbidden = ["script_run", "mpremote", "curl", "git", "esptool"]
    offenders = []

    for skill in MAIN_CHAIN:
        text = (ROOT / skill / "SKILL.md").read_text(encoding="utf-8").lower()
        for token in forbidden:
            if token in text:
                offenders.append(f"{skill}: {token}")

    assert offenders == []
