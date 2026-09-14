"""Structural analyzer and downgrade-risk classification."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from xml.etree.ElementTree import Element, ElementTree

# Live 12 native / structure markers evidenced by public converter research
LIVE12_DEVICE_TAGS = {
    "InstrumentMeld": "Native Live 12 Meld device",
    "Roar": "Native Live 12 Roar device",
}
LIVE12_STRUCTURE_TAGS = {
    "ContentLanes": "Live 12 content/take-lane oriented structure",
    "ExpressionLanes": "Live 12 expression lanes",
    "MxPatchRef": "Max patch ref removed by public 12->11 converter",
    "Oversampling": "Oversampling node removed by public 12->11 converter",
}

PLUGIN_TAGS = {
    "PluginDevice": "third-party plugin (generic)",
    "AuPluginDevice": "AU plugin",
    "Vst3PluginDevice": "VST3 plugin",
    "VstPluginDevice": "VST2 plugin",
}
MAX_TAGS = {
    "MxDeviceAudioEffect": "Max for Live audio effect",
    "MxDeviceInstrument": "Max for Live instrument",
    "MxDeviceMidiEffect": "Max for Live MIDI effect",
}


class RiskClass(str, Enum):
    SAFE = "SAFE"
    TRANSFORMABLE = "TRANSFORMABLE"
    UNSUPPORTED = "UNSUPPORTED"
    UNKNOWN = "UNKNOWN"


@dataclass
class Finding:
    category: RiskClass
    kind: str
    detail: str
    count: int = 1


@dataclass
class StructuralSnapshot:
    audio_tracks: int = 0
    midi_tracks: int = 0
    group_tracks: int = 0
    return_tracks: int = 0
    other_tracks: int = 0
    scenes: int = 0
    audio_clips: int = 0
    midi_clips: int = 0
    midi_notes: int = 0
    native_devices: int = 0
    plugin_devices: int = 0
    max_devices: int = 0
    sample_refs: int = 0
    tempo: str | None = None
    track_names: list[str] = field(default_factory=list)

    @property
    def total_tracks(self) -> int:
        return (
            self.audio_tracks
            + self.midi_tracks
            + self.group_tracks
            + self.return_tracks
            + self.other_tracks
        )


@dataclass
class AnalysisReport:
    snapshot: StructuralSnapshot
    findings: list[Finding]
    live12_blocker_tags: dict[str, int]


def _track_name(track: Element) -> str:
    name_el = track.find("Name")
    if name_el is not None:
        for key in ("EffectiveName", "UserName", "MemorizedFirstClipName"):
            child = name_el.find(key)
            if child is not None and child.attrib.get("Value"):
                return child.attrib["Value"]
    return track.attrib.get("Id", track.tag)


def build_snapshot(tree: ElementTree) -> StructuralSnapshot:
    root = tree.getroot()
    snap = StructuralSnapshot()
    tracks_parent = root.find("./LiveSet/Tracks")
    if tracks_parent is not None:
        for child in list(tracks_parent):
            tag = child.tag
            if tag == "AudioTrack":
                snap.audio_tracks += 1
            elif tag == "MidiTrack":
                snap.midi_tracks += 1
            elif tag == "GroupTrack":
                snap.group_tracks += 1
            elif tag == "ReturnTrack":
                snap.return_tracks += 1
            else:
                snap.other_tracks += 1
            snap.track_names.append(_track_name(child))

    snap.scenes = len(root.findall(".//Scene"))
    snap.audio_clips = len(root.findall(".//AudioClip"))
    snap.midi_clips = len(root.findall(".//MidiClip"))
    snap.midi_notes = len(root.findall(".//MidiNoteEvent"))
    snap.sample_refs = len(root.findall(".//SampleRef"))

    # Devices: count leaf-ish device tags under DeviceChain
    plugin_count = 0
    max_count = 0
    native_count = 0
    for el in root.iter():
        if el.tag in PLUGIN_TAGS:
            plugin_count += 1
        elif el.tag in MAX_TAGS:
            max_count += 1
        elif el.tag in LIVE12_DEVICE_TAGS:
            native_count += 1
        elif el.tag.endswith("Device") and el.tag not in {
            "DeviceChain",
            "Devices",
            "DeviceChainWrapper",
        }:
            # Heuristic native / other devices
            if "Plugin" not in el.tag and not el.tag.startswith("Mx"):
                native_count += 1

    snap.plugin_devices = plugin_count
    snap.max_devices = max_count
    snap.native_devices = native_count

    tempo_manual = root.find(".//Tempo/Manual")
    if tempo_manual is not None:
        snap.tempo = tempo_manual.attrib.get("Value")
    return snap


def analyze_for_target(tree: ElementTree, target_major: int = 11) -> AnalysisReport:
    snap = build_snapshot(tree)
    findings: list[Finding] = []
    blockers: dict[str, int] = {}
    root = tree.getroot()

    if target_major == 11:
        for tag, reason in {**LIVE12_DEVICE_TAGS, **LIVE12_STRUCTURE_TAGS}.items():
            nodes = root.findall(f".//{tag}")
            if nodes:
                blockers[tag] = len(nodes)
                category = (
                    RiskClass.UNSUPPORTED
                    if tag in LIVE12_DEVICE_TAGS
                    else RiskClass.TRANSFORMABLE
                )
                findings.append(
                    Finding(
                        category=category,
                        kind=tag,
                        detail=reason,
                        count=len(nodes),
                    )
                )

        main_routes = 0
        for el in root.iter():
            for attr_val in el.attrib.values():
                if "AudioOut/Main" in attr_val:
                    main_routes += 1
            if el.text and "AudioOut/Main" in el.text:
                main_routes += 1
        if main_routes:
            findings.append(
                Finding(
                    RiskClass.TRANSFORMABLE,
                    "AudioOut/Main",
                    "Routing path Main->Master for Live 11",
                    main_routes,
                )
            )

        if snap.max_devices:
            findings.append(
                Finding(
                    RiskClass.UNKNOWN,
                    "MaxForLive",
                    "Max for Live devices preserved but unverified on Live 11",
                    snap.max_devices,
                )
            )
        if snap.plugin_devices:
            findings.append(
                Finding(
                    RiskClass.SAFE,
                    "ThirdPartyPlugins",
                    "Plugin wrappers/state preserved structurally; host presence unknown",
                    snap.plugin_devices,
                )
            )

        # Compatible baseline structures
        findings.append(
            Finding(
                RiskClass.SAFE,
                "CoreTracksClips",
                "Tracks/clips/tempo structures common to Live 11/12",
                snap.total_tracks + snap.audio_clips + snap.midi_clips,
            )
        )

    return AnalysisReport(snapshot=snap, findings=findings, live12_blocker_tags=blockers)


def compare_snapshots(
    before: StructuralSnapshot, after: StructuralSnapshot
) -> list[str]:
    """Return list of unexpected loss messages."""
    errors: list[str] = []
    checks = [
        ("audio_tracks", before.audio_tracks, after.audio_tracks),
        ("midi_tracks", before.midi_tracks, after.midi_tracks),
        ("group_tracks", before.group_tracks, after.group_tracks),
        ("return_tracks", before.return_tracks, after.return_tracks),
        ("audio_clips", before.audio_clips, after.audio_clips),
        ("midi_clips", before.midi_clips, after.midi_clips),
        ("midi_notes", before.midi_notes, after.midi_notes),
        ("sample_refs", before.sample_refs, after.sample_refs),
        ("plugin_devices", before.plugin_devices, after.plugin_devices),
    ]
    for name, b, a in checks:
        if a < b:
            errors.append(f"Unexpected loss of {name}: {b} -> {a}")
    if before.tempo and after.tempo and before.tempo != after.tempo:
        errors.append(f"Tempo changed: {before.tempo} -> {after.tempo}")
    if before.track_names != after.track_names:
        # Names should preserve for non-destructive paths
        if len(before.track_names) != len(after.track_names):
            errors.append("Track name list length changed")
        else:
            for i, (x, y) in enumerate(zip(before.track_names, after.track_names)):
                if x != y:
                    errors.append(f"Track name changed at index {i}: {x!r} -> {y!r}")
    return errors
