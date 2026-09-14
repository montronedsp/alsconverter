from __future__ import annotations

from pathlib import Path

from alsdowngrade.gzip_io import decompress_als, load_als_xml_bytes, unique_output_path
from alsdowngrade.parser import AlsParseError, parse_als_xml
from alsdowngrade.version import parse_set_version, version_from_tree
import pytest


def test_load_and_parse_live12(live12_minimal: Path) -> None:
    compressed, xml = load_als_xml_bytes(live12_minimal)
    assert compressed[:2] == b"\x1f\x8b"
    tree = parse_als_xml(xml)
    v = version_from_tree(tree)
    assert v.marketing_major == 12
    assert v.major_version == "5"
    assert v.schema_change_count == "7"


def test_rejects_xxe() -> None:
    evil = b'<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe "x">]><Ableton><LiveSet/></Ableton>'
    with pytest.raises(AlsParseError):
        parse_als_xml(evil)


def test_unique_output_path(tmp_path: Path) -> None:
    p = tmp_path / "a.als"
    p.write_bytes(b"x")
    u = unique_output_path(p)
    assert u.name == "a_1.als"
    u.write_bytes(b"y")
    u2 = unique_output_path(p)
    assert u2.name == "a_2.als"


def test_source_untouched_after_read(live12_minimal: Path) -> None:
    before = live12_minimal.read_bytes()
    load_als_xml_bytes(live12_minimal)
    assert live12_minimal.read_bytes() == before
