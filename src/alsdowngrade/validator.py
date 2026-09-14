"""Multi-layer validation for generated ALS files."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from alsdowngrade.analyzer import StructuralSnapshot, build_snapshot, compare_snapshots
from alsdowngrade.gzip_io import compress_als, decompress_als, load_als_xml_bytes
from alsdowngrade.parser import parse_als_xml, serialize_als_xml
from alsdowngrade.transforms.live12_to_11 import LIVE12_TO_11_RULES
from alsdowngrade.transforms.base import Action


@dataclass
class ValidationResult:
    ok: bool
    layers: dict[str, bool] = field(default_factory=dict)
    messages: list[str] = field(default_factory=list)
    leftover_source_markers: dict[str, int] = field(default_factory=dict)


def validate_generated(
    output_path: Path,
    *,
    before: StructuralSnapshot | None = None,
    expect_cleared_tags: list[str] | None = None,
) -> ValidationResult:
    result = ValidationResult(ok=True)
    path = Path(output_path)

    # Layer 1 - container
    try:
        compressed, xml_bytes = load_als_xml_bytes(path)
        if not compressed:
            raise ValueError("empty")
        result.layers["container"] = True
    except Exception as exc:  # noqa: BLE001 - report as validation failure
        result.ok = False
        result.layers["container"] = False
        result.messages.append(f"Layer1 container FAIL: {exc}")
        return result

    # Layer 2 - XML
    try:
        tree = parse_als_xml(xml_bytes)
        result.layers["xml"] = True
    except Exception as exc:  # noqa: BLE001
        result.ok = False
        result.layers["xml"] = False
        result.messages.append(f"Layer2 XML FAIL: {exc}")
        return result

    # Layer 3 - structural
    after = build_snapshot(tree)
    if before is not None:
        losses = compare_snapshots(before, after)
        # Removals of Live12 devices may reduce native_devices - that's expected;
        # compare_snapshots ignores native_devices intentionally.
        if losses:
            result.ok = False
            result.layers["structural"] = False
            result.messages.extend(f"Layer3 structural FAIL: {m}" for m in losses)
        else:
            result.layers["structural"] = True
    else:
        result.layers["structural"] = True

    # Layer 4 - leftover source-only markers (for compatible conversion)
    leftovers: dict[str, int] = {}
    if expect_cleared_tags:
        root = tree.getroot()
        for tag in expect_cleared_tags:
            n = len(root.findall(f".//{tag}"))
            if n:
                leftovers[tag] = n
        result.leftover_source_markers = leftovers
        if leftovers:
            result.ok = False
            result.layers["target_schema"] = False
            result.messages.append(
                f"Layer4 target schema FAIL: leftover markers {leftovers}"
            )
        else:
            result.layers["target_schema"] = True
    else:
        result.layers["target_schema"] = True

    # Layer 5 - round trip
    try:
        xml2 = serialize_als_xml(tree)
        gz2 = compress_als(xml2)
        xml3 = decompress_als(gz2)
        parse_als_xml(xml3)
        result.layers["round_trip"] = True
    except Exception as exc:  # noqa: BLE001
        result.ok = False
        result.layers["round_trip"] = False
        result.messages.append(f"Layer5 round-trip FAIL: {exc}")

    # Layer 6 is human Live open - never auto-claimed
    result.layers["real_ableton"] = False
    result.messages.append(
        "Layer6 real Ableton Live opening test: NOT YET VERIFIED"
    )
    return result


def tags_removed_by_compatible_profile() -> list[str]:
    return [
        r.selector
        for r in LIVE12_TO_11_RULES
        if r.action == Action.REMOVE and "compatible" in r.modes
    ]
