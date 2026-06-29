from pathlib import Path

from browser_skill_contract.runtime import load_manifest

ROOT = Path(__file__).resolve().parents[1]
TIERS = {"orchestrator", "phase", "atomic", "tool"}
SPINES = {"project_pipeline", "driver_normalization", "shared"}


def test_every_browser_skill_has_tier_and_spine():
    catalog = load_manifest()
    bad = []
    for skill in sorted(catalog.browser_skills):
        meta = catalog.orchestration_for(skill)
        if meta.get("tier") not in TIERS:
            bad.append(f"{skill}: tier={meta.get('tier')!r}")
        if meta.get("spine") not in SPINES:
            bad.append(f"{skill}: spine={meta.get('spine')!r}")
    assert bad == []


def test_orchestrates_and_calls_reference_real_browser_skills():
    catalog = load_manifest()
    dangling = []
    for skill in sorted(catalog.browser_skills):
        meta = catalog.orchestration_for(skill)
        for edge in ("orchestrates", "calls"):
            for target in meta.get(edge, []):
                if target not in catalog.browser_skills:
                    dangling.append(f"{skill}.{edge} -> {target}")
    assert dangling == []


def test_orchestrator_docs_declare_an_orchestration_section():
    catalog = load_manifest()
    missing = []
    for skill in sorted(catalog.browser_skills):
        meta = catalog.orchestration_for(skill)
        if meta.get("tier") != "orchestrator":
            continue
        text = (ROOT / skill / "SKILL.md").read_text(encoding="utf-8").lower()
        if "## orchestration" not in text:
            missing.append(skill)
        if not meta.get("orchestrates"):
            missing.append(f"{skill}: empty orchestrates")
    assert missing == []
