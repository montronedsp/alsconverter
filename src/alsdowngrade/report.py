"""Human-readable reports for CLI."""

from __future__ import annotations

from alsdowngrade.analyzer import AnalysisReport, RiskClass, build_snapshot
from alsdowngrade.converter import ConversionReport
from alsdowngrade.version import SetVersion


def format_inspect(path: str, version: SetVersion, analysis: AnalysisReport) -> str:
    snap = analysis.snapshot
    blockers = analysis.live12_blocker_tags
    lines = [
        "Ableton Live Set",
        f"Path: {path}",
        f"Creator: {version.creator}",
        f"Internal MajorVersion: {version.major_version}",
        f"MinorVersion: {version.minor_version}",
        f"SchemaChangeCount: {version.schema_change_count}",
        f"Revision: {version.revision}",
        f"Detected marketing version: {version.label}",
        f"Tracks: {snap.total_tracks}",
        f"Audio tracks: {snap.audio_tracks}",
        f"MIDI tracks: {snap.midi_tracks}",
        f"Group tracks: {snap.group_tracks}",
        f"Return tracks: {snap.return_tracks}",
        f"Scenes: {snap.scenes}",
        f"Audio clips: {snap.audio_clips}",
        f"MIDI clips: {snap.midi_clips}",
        f"MIDI note events: {snap.midi_notes}",
        f"Native devices (heuristic): {snap.native_devices}",
        f"Third-party plugin devices: {snap.plugin_devices}",
        f"Max for Live devices: {snap.max_devices}",
        f"Tempo: {snap.tempo or 'UNKNOWN'}",
    ]
    if blockers:
        lines.append("Potential downgrade blockers:")
        for tag, count in sorted(blockers.items()):
            lines.append(f"  - {tag} x {count}")
    else:
        lines.append("Potential downgrade blockers: none detected by current rules")

    by_cat: dict[str, list[str]] = {c.value: [] for c in RiskClass}
    for f in analysis.findings:
        by_cat[f.category.value].append(f"{f.kind}: {f.detail} (x{f.count})")
    lines.append("Compatibility categories:")
    for cat in RiskClass:
        items = by_cat[cat.value]
        lines.append(f"  {cat.value}: {len(items)}")
        for item in items[:12]:
            lines.append(f"    - {item}")
    lines.append("")
    lines.append("ORIGINAL FILE IS NEVER MODIFIED by inspect/analyze.")
    return "\n".join(lines)


def format_conversion(report: ConversionReport) -> str:
    lines = [
        f"Outcome: {report.outcome.value}",
        "Source:",
        f"  {report.source_path}",
        f"  {report.source_creator}",
        "Target:",
        f"  Ableton Live {report.target_label}",
        f"Mode: {report.mode}",
    ]
    if report.output_path:
        lines += ["Output:", f"  {report.output_path}"]
    else:
        lines += ["Output:", "  (none - refused or invalid)"]

    if report.reason:
        lines += ["Reason:", report.reason]

    if report.preserved:
        lines.append("Preserved:")
        for k, v in report.preserved.items():
            lines.append(f"  {k}: {v}")

    if report.modified:
        lines.append("Modified:")
        for m in report.modified:
            lines.append(f"  {m}")

    if report.removed:
        lines.append("Removed:")
        for m in report.removed:
            lines.append(f"  {m}")

    if report.warnings:
        lines.append("Warnings:")
        for w in report.warnings:
            lines.append(f"  {w}")

    if not report.output_path:
        static = "N/A"
    elif any("FAIL" in m for m in report.validation_messages):
        static = "FAIL"
    else:
        static = "PASS"

    lines += [
        f"Static validation: {static}",
        "Real Ableton Live opening test: NOT YET VERIFIED",
        "",
        "ORIGINAL FILE IS NEVER MODIFIED",
    ]
    return "\n".join(lines)
