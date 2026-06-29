from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAIN_CHAIN = [
    "upy-analyze-browser",
    "upy-select-hw-browser",
    "upy-flash-mpy-firmware-browser",
    "upy-scaffold-browser",
    "upy-generate-browser",
    "upy-deploy-browser",
]
REQUIRED_SECTIONS = [
    "## purpose",
    "## plugin equivalence",
    "## inputs",
    "## outputs",
    "## blockless primitive sequence",
    "## runtime state and partial results",
    "## failure conditions",
]


def test_main_chain_skill_docs_declare_contract_sections():
    missing = []

    for skill in MAIN_CHAIN:
        text = (ROOT / skill / "SKILL.md").read_text(encoding="utf-8").lower()
        for heading in REQUIRED_SECTIONS:
            if heading not in text:
                missing.append(f"{skill}: {heading}")

    assert missing == []


def test_main_chain_skill_docs_do_not_expose_local_commands_as_actions():
    # Ban the local-command *invocations* (with trailing space), consistent with
    # test_browser_conversion_contract; bare substrings would false-positive on
    # legitimate identifiers like "github" (a driver-source enum) and ".gitkeep".
    forbidden = ["script_run", "mpremote ", "curl ", "git ", "esptool"]
    offenders = []

    for skill in MAIN_CHAIN:
        text = (ROOT / skill / "SKILL.md").read_text(encoding="utf-8").lower()
        for token in forbidden:
            if token in text:
                offenders.append(f"{skill}: {token}")

    assert offenders == []


def test_all_browser_skill_docs_declare_plugin_equivalent_contract_sections():
    missing = []

    for skill_file in sorted(ROOT.glob("*-browser/SKILL.md")):
        text = skill_file.read_text(encoding="utf-8").lower()
        for heading in REQUIRED_SECTIONS:
            if heading not in text:
                missing.append(f"{skill_file.parent.name}: {heading}")

    assert missing == []


def test_browser_skill_docs_are_blockless_first_without_impossibility_claims():
    forbidden_phrases = [
        "browser cannot",
        "cannot implement",
        "not possible in browser",
        "impossible in browser",
        "unsupported in browser",
    ]
    offenders = []

    for skill_file in sorted(ROOT.glob("*-browser/SKILL.md")):
        text = skill_file.read_text(encoding="utf-8").lower()
        if "blockless web builder" not in text:
            offenders.append(f"{skill_file.parent.name}: missing Blockless Web Builder")
        for phrase in forbidden_phrases:
            if phrase in text:
                offenders.append(f"{skill_file.parent.name}: {phrase}")

    assert offenders == []
