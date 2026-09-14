from __future__ import annotations

from pathlib import Path

from alsdowngrade.analyzer import RiskClass, analyze_for_target
from alsdowngrade.diff import diff_als
from alsdowngrade.gzip_io import load_als_xml_bytes
from alsdowngrade.parser import parse_als_xml


def test_analyze_detects_blockers(live12_blocked: Path) -> None:
    _, xml = load_als_xml_bytes(live12_blocked)
    tree = parse_als_xml(xml)
    report = analyze_for_target(tree, target_major=11)
    assert "InstrumentMeld" in report.live12_blocker_tags
    assert "Roar" in report.live12_blocker_tags
    cats = {f.category for f in report.findings}
    assert RiskClass.UNSUPPORTED in cats
    assert RiskClass.TRANSFORMABLE in cats


def test_diff_root_and_added_tags(live11_minimal: Path, live12_blocked: Path) -> None:
    report = diff_als(live11_minimal, live12_blocked)
    assert "Creator" in report.root_attr_diffs
    assert "MinorVersion" in report.root_attr_diffs
    assert report.root_attr_diffs["SchemaChangeCount"][0] == "3"
    assert report.root_attr_diffs["SchemaChangeCount"][1] == "7"
    assert "InstrumentMeld" in report.added_tags or "Roar" in report.added_tags
