from __future__ import annotations

from pathlib import Path

from alsdowngrade.converter import Outcome, convert_als
from alsdowngrade.gzip_io import load_als_xml_bytes
from alsdowngrade.parser import parse_als_xml
from alsdowngrade.version import version_from_tree


def test_conservative_clean_live12(live12_minimal: Path, tmp_path: Path) -> None:
    before = live12_minimal.read_bytes()
    report = convert_als(
        live12_minimal,
        target="11.2",
        mode="conservative",
        output_dir=tmp_path,
    )
    assert live12_minimal.read_bytes() == before
    assert report.output_path is not None
    assert report.outcome in {Outcome.EXPERIMENTAL, Outcome.SUCCESS_WITH_WARNINGS}
    _, xml = load_als_xml_bytes(Path(report.output_path))
    tree = parse_als_xml(xml)
    v = version_from_tree(tree)
    assert v.creator == "Ableton Live 11.2.11"
    assert v.minor_version == "11.0_11202"
    assert v.schema_change_count == "17"
    # Routing normalized
    assert b"AudioOut/Main" not in xml
    assert b"AudioOut/Master" in xml


def test_target_11_3_fingerprint(live12_minimal: Path, tmp_path: Path) -> None:
    report = convert_als(
        live12_minimal,
        target="11.3",
        mode="conservative",
        output_dir=tmp_path,
    )
    assert report.output_path is not None
    _, xml = load_als_xml_bytes(Path(report.output_path))
    v = version_from_tree(parse_als_xml(xml))
    assert v.creator == "Ableton Live 11.3.21"
    assert v.minor_version == "11.0_11300"
    assert v.schema_change_count == "3"


def test_target_11_2_7_fingerprint(live12_minimal: Path, tmp_path: Path) -> None:
    report = convert_als(
        live12_minimal,
        target="11.2.7",
        mode="conservative",
        output_dir=tmp_path,
    )
    assert report.output_path is not None
    _, xml = load_als_xml_bytes(Path(report.output_path))
    v = version_from_tree(parse_als_xml(xml))
    assert v.creator == "Ableton Live 11.2.7"
    assert v.minor_version == "11.0_11202"
    assert v.schema_change_count == "11"

def test_conservative_refuses_blockers(live12_blocked: Path, tmp_path: Path) -> None:
    before = live12_blocked.read_bytes()
    report = convert_als(
        live12_blocked,
        target="11",
        mode="conservative",
        output_dir=tmp_path,
    )
    assert report.outcome == Outcome.REFUSED_UNSUPPORTED
    assert report.output_path is None
    assert live12_blocked.read_bytes() == before
    assert list(tmp_path.glob("*.als")) == []


def test_compatible_removes_l12_nodes(live12_blocked: Path, tmp_path: Path) -> None:
    before = live12_blocked.read_bytes()
    report = convert_als(
        live12_blocked,
        target="11",
        mode="compatible",
        output_dir=tmp_path,
    )
    assert live12_blocked.read_bytes() == before
    assert report.output_path is not None
    _, xml = load_als_xml_bytes(Path(report.output_path))
    assert b"InstrumentMeld" not in xml
    assert b"Roar" not in xml
    assert b"ContentLanes" not in xml
    assert b"ExpressionLanes" not in xml
    assert b"PluginDevice" in xml  # third-party preserved
    assert report.preserved["tracks"] == 2
    assert report.preserved["midi_clips"] == 1
    assert report.preserved["audio_clips"] == 1
    assert report.live_open_verified is False


def test_never_overwrite(live12_minimal: Path, tmp_path: Path) -> None:
    out = tmp_path / "fixed.als"
    out.write_bytes(b"sentinel")
    report = convert_als(
        live12_minimal,
        target="11",
        mode="conservative",
        output=out,
    )
    assert report.output_path is not None
    assert Path(report.output_path).name == "fixed_1.als"
    assert out.read_bytes() == b"sentinel"


def test_already_live11_refused(live11_minimal: Path, tmp_path: Path) -> None:
    report = convert_als(live11_minimal, target="11", output_dir=tmp_path)
    assert report.outcome == Outcome.REFUSED_UNSUPPORTED
