"""Conversion orchestration - never touches the source file on disk beyond reading."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from alsdowngrade.analyzer import (
    AnalysisReport,
    RiskClass,
    analyze_for_target,
    build_snapshot,
)
from alsdowngrade.gzip_io import (
    compress_als,
    default_output_path,
    load_als_xml_bytes,
    write_new_als,
)
from alsdowngrade.parser import parse_als_xml, serialize_als_xml
from alsdowngrade.transforms.live12_to_11 import (
    CONSERVATIVE_BLOCKER_TAGS,
    apply_live12_to_11,
)
from alsdowngrade.validator import tags_removed_by_compatible_profile, validate_generated
from alsdowngrade.version import (
    is_live11_family,
    is_live12_family,
    resolve_target_fingerprint,
    version_from_tree,
)


class Outcome(str, Enum):
    SUCCESS = "SUCCESS"
    SUCCESS_WITH_WARNINGS = "SUCCESS_WITH_WARNINGS"
    EXPERIMENTAL = "EXPERIMENTAL"
    REFUSED_UNSUPPORTED = "REFUSED_UNSUPPORTED"
    INVALID_INPUT = "INVALID_INPUT"


@dataclass
class ConversionReport:
    outcome: Outcome
    source_path: str
    output_path: str | None
    source_creator: str
    target_label: str
    mode: str
    preserved: dict[str, int | str] = field(default_factory=dict)
    modified: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    analysis: AnalysisReport | None = None
    validation_messages: list[str] = field(default_factory=list)
    reason: str | None = None
    live_open_verified: bool = False


def convert_als(
    source: Path | str,
    *,
    target: str = "11.2",
    mode: str = "conservative",
    output: Path | str | None = None,
    output_dir: Path | str | None = None,
) -> ConversionReport:
    source_path = Path(source)
    mode = mode.lower()
    try:
        fp = resolve_target_fingerprint(target)
    except ValueError as exc:
        return ConversionReport(
            outcome=Outcome.REFUSED_UNSUPPORTED,
            source_path=str(source_path),
            output_path=None,
            source_creator="",
            target_label=str(target),
            mode=mode,
            reason=str(exc),
        )

    try:
        _compressed, xml_bytes = load_als_xml_bytes(source_path)
        tree = parse_als_xml(xml_bytes)
    except Exception as exc:  # noqa: BLE001
        return ConversionReport(
            outcome=Outcome.INVALID_INPUT,
            source_path=str(source_path),
            output_path=None,
            source_creator="",
            target_label=fp["target_label"],
            mode=mode,
            reason=str(exc),
        )

    version = version_from_tree(tree)
    analysis = analyze_for_target(tree, target_major=11)
    before = build_snapshot(tree)

    if is_live11_family(version) and not is_live12_family(version):
        return ConversionReport(
            outcome=Outcome.REFUSED_UNSUPPORTED,
            source_path=str(source_path),
            output_path=None,
            source_creator=version.creator,
            target_label=fp["target_label"],
            mode=mode,
            analysis=analysis,
            reason="Source already appears to be Live 11 family; nothing to downgrade.",
        )

    if not is_live12_family(version):
        return ConversionReport(
            outcome=Outcome.REFUSED_UNSUPPORTED,
            source_path=str(source_path),
            output_path=None,
            source_creator=version.creator,
            target_label=fp["target_label"],
            mode=mode,
            analysis=analysis,
            reason=(
                f"Source does not look like Live 12 (Creator={version.creator!r}, "
                f"MinorVersion={version.minor_version!r}). Milestone 1 only converts 12->11."
            ),
        )

    # Conservative refusal if known blockers present
    if mode == "conservative":
        present = {
            tag: analysis.live12_blocker_tags[tag]
            for tag in CONSERVATIVE_BLOCKER_TAGS
            if tag in analysis.live12_blocker_tags
        }
        if present:
            detail = ", ".join(f"{k} x{v}" for k, v in present.items())
            return ConversionReport(
                outcome=Outcome.REFUSED_UNSUPPORTED,
                source_path=str(source_path),
                output_path=None,
                source_creator=version.creator,
                target_label=fp["target_label"],
                mode=mode,
                analysis=analysis,
                reason=(
                    "Conversion refused safely. Original file untouched.\n"
                    "Reason: Conservative mode found known Live 12-only constructs: "
                    f"{detail}. Re-run with --mode compatible or --mode salvage."
                ),
            )

    transform = apply_live12_to_11(tree, mode=mode, target=target)
    xml_out = serialize_als_xml(tree)
    # Also ensure AudioOut replacement at serialized level (belt+suspenders for text nodes)
    xml_text = xml_out.decode("utf-8").replace("AudioOut/Main", "AudioOut/Master")
    xml_out = xml_text.encode("utf-8")
    # Re-parse after text replace to keep tree consistent for validation
    tree = parse_als_xml(xml_out)
    compressed_out = compress_als(xml_out)

    if output is not None:
        out_path = Path(output)
        if out_path.exists():
            from alsdowngrade.gzip_io import unique_output_path

            out_path = unique_output_path(out_path)
    else:
        out_dir = Path(output_dir) if output_dir else Path("output")
        out_path = default_output_path(source_path, fp["target_label"], out_dir)

    written = write_new_als(out_path, compressed_out)

    expect_clear = (
        tags_removed_by_compatible_profile()
        if mode in {"compatible", "salvage"}
        else None
    )
    # For structural compare after compatible removals, native device counts may drop;
    # rebuild expected "before" for clip/track preservation only.
    validation = validate_generated(
        written, before=before, expect_cleared_tags=expect_clear
    )

    removed = [
        f"{e.count}x {e.detail}" for e in transform.events if e.action == "remove"
    ]
    modified = [
        e.detail for e in transform.events if e.action != "remove"
    ]
    warnings = list(transform.warnings)
    for f in analysis.findings:
        if f.category in {RiskClass.UNKNOWN, RiskClass.UNSUPPORTED}:
            warnings.append(f"{f.category.value}: {f.kind} - {f.detail} (x{f.count})")

    if not validation.ok:
        # File was written but static validation failed - still report honestly
        outcome = Outcome.EXPERIMENTAL
        warnings.extend(validation.messages)
    elif warnings:
        outcome = Outcome.SUCCESS_WITH_WARNINGS
    else:
        # Schema path is experimental until Live-tested
        outcome = Outcome.EXPERIMENTAL

    after = build_snapshot(tree)
    return ConversionReport(
        outcome=outcome,
        source_path=str(source_path.resolve()),
        output_path=str(written.resolve()),
        source_creator=version.creator,
        target_label=fp["target_label"],
        mode=mode,
        preserved={
            "tracks": after.total_tracks,
            "midi_clips": after.midi_clips,
            "audio_clips": after.audio_clips,
            "midi_notes": after.midi_notes,
            "plugin_devices": after.plugin_devices,
            "tempo": after.tempo or "",
        },
        modified=modified,
        removed=removed,
        warnings=warnings,
        analysis=analysis,
        validation_messages=validation.messages,
        live_open_verified=False,
    )
