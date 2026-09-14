"""Structural XML differential analysis for forensic research."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from xml.etree.ElementTree import Element, ElementTree

from alsdowngrade.gzip_io import load_als_xml_bytes
from alsdowngrade.parser import parse_als_xml
from alsdowngrade.version import version_from_tree

VOLATILE_ATTRS = {
    "Revision",
    "Id",
    "LomId",
    "PointeeId",
    "Time",
}
VOLATILE_TAGS = {
    # Often change without semantic meaning for schema research
}


@dataclass
class DiffReport:
    left_path: str
    right_path: str
    root_attr_diffs: dict[str, tuple[str | None, str | None]] = field(default_factory=dict)
    added_tags: dict[str, int] = field(default_factory=dict)
    removed_tags: dict[str, int] = field(default_factory=dict)
    tag_count_deltas: dict[str, tuple[int, int]] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


def _tag_counts(root: Element) -> Counter[str]:
    c: Counter[str] = Counter()
    for el in root.iter():
        c[el.tag] += 1
    return c


def _normalize_tree(tree: ElementTree) -> ElementTree:
    """Strip volatile attributes for research diffs (in-memory only)."""
    root = tree.getroot()
    for el in root.iter():
        for attr in list(el.attrib):
            if attr in VOLATILE_ATTRS or attr.endswith("Id"):
                # Keep Ableton root version attrs
                if el.tag == "Ableton" and attr in {
                    "MajorVersion",
                    "MinorVersion",
                    "SchemaChangeCount",
                    "Creator",
                    "Revision",
                }:
                    if attr == "Revision":
                        el.attrib.pop(attr, None)
                    continue
                if el.tag == "Ableton":
                    continue
                el.attrib.pop(attr, None)
    # Clear Ableton Revision always when normalizing
    if "Revision" in root.attrib:
        del root.attrib["Revision"]
    return tree


def diff_als(
    left: Path | str,
    right: Path | str,
    *,
    normalize: bool = False,
) -> DiffReport:
    left_p, right_p = Path(left), Path(right)
    _, left_xml = load_als_xml_bytes(left_p)
    _, right_xml = load_als_xml_bytes(right_p)
    left_tree = parse_als_xml(left_xml)
    right_tree = parse_als_xml(right_xml)
    if normalize:
        left_tree = _normalize_tree(left_tree)
        right_tree = _normalize_tree(right_tree)

    lv = version_from_tree(left_tree)
    rv = version_from_tree(right_tree)
    report = DiffReport(left_path=str(left_p), right_path=str(right_p))
    report.notes.append(f"Left Creator: {lv.creator} (MinorVersion={lv.minor_version})")
    report.notes.append(f"Right Creator: {rv.creator} (MinorVersion={rv.minor_version})")
    report.notes.append(
        f"SchemaChangeCount: {lv.schema_change_count} -> {rv.schema_change_count}"
    )

    lroot, rroot = left_tree.getroot(), right_tree.getroot()
    keys = sorted(set(lroot.attrib) | set(rroot.attrib))
    for k in keys:
        lv_a, rv_a = lroot.attrib.get(k), rroot.attrib.get(k)
        if lv_a != rv_a:
            report.root_attr_diffs[k] = (lv_a, rv_a)

    lc, rc = _tag_counts(lroot), _tag_counts(rroot)
    all_tags = sorted(set(lc) | set(rc))
    for tag in all_tags:
        a, b = lc.get(tag, 0), rc.get(tag, 0)
        if a != b:
            report.tag_count_deltas[tag] = (a, b)
        if a == 0 and b > 0:
            report.added_tags[tag] = b
        if b == 0 and a > 0:
            report.removed_tags[tag] = a

    report.notes.append(
        "IDs/Revisions/timestamps are unstable; use --normalize for schema-focused diffs."
    )
    return report


def format_diff(report: DiffReport) -> str:
    lines = [
        "ALS structural diff",
        f"Left:  {report.left_path}",
        f"Right: {report.right_path}",
        "",
        "Notes:",
    ]
    lines.extend(f"  {n}" for n in report.notes)
    lines.append("")
    lines.append("Root attribute differences:")
    if not report.root_attr_diffs:
        lines.append("  (none)")
    else:
        for k, (a, b) in sorted(report.root_attr_diffs.items()):
            lines.append(f"  {k}: {a!r} -> {b!r}")

    lines.append("")
    lines.append("Added element types (present only on right):")
    if not report.added_tags:
        lines.append("  (none)")
    else:
        for tag, n in sorted(report.added_tags.items(), key=lambda x: (-x[1], x[0])):
            lines.append(f"  + {tag} x {n}")

    lines.append("")
    lines.append("Removed element types (present only on left):")
    if not report.removed_tags:
        lines.append("  (none)")
    else:
        for tag, n in sorted(report.removed_tags.items(), key=lambda x: (-x[1], x[0])):
            lines.append(f"  - {tag} x {n}")

    lines.append("")
    lines.append("Tag count deltas (left -> right):")
    shown = 0
    for tag, (a, b) in sorted(
        report.tag_count_deltas.items(), key=lambda x: (-abs(x[1][1] - x[1][0]), x[0])
    ):
        lines.append(f"  {tag}: {a} -> {b}")
        shown += 1
        if shown >= 80:
            lines.append("  ... truncated ...")
            break
    return "\n".join(lines)
