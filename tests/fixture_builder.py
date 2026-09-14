"""Synthetic ALS builders for tests."""

from __future__ import annotations

import gzip
import io
from pathlib import Path
from xml.etree.ElementTree import Element, ElementTree, SubElement


def _set_value(parent: Element, tag: str, value: str) -> Element:
    el = SubElement(parent, tag)
    el.set("Value", value)
    return el


def build_minimal_live12_xml(
    *,
    with_live12_nodes: bool = False,
    with_plugin: bool = False,
    tempo: str = "120",
) -> bytes:
    root = Element(
        "Ableton",
        {
            "MajorVersion": "5",
            "MinorVersion": "12.0_12049",
            "SchemaChangeCount": "7",
            "Creator": "Ableton Live 12.0.1",
            "Revision": "dc76d800e94bdd5e2d8f0f72ef4d056a634a8cd7",
        },
    )
    live_set = SubElement(root, "LiveSet")
    tracks = SubElement(live_set, "Tracks")

    midi = SubElement(tracks, "MidiTrack", {"Id": "1"})
    name = SubElement(midi, "Name")
    _set_value(name, "EffectiveName", "Synth")
    chain = SubElement(midi, "DeviceChain")
    devices = SubElement(chain, "Devices")
    if with_live12_nodes:
        meld = SubElement(devices, "InstrumentMeld", {"Id": "9"})
        SubElement(meld, "ContentLanes")
        SubElement(meld, "ExpressionLanes")
        SubElement(meld, "Oversampling")
        roar = SubElement(devices, "Roar", {"Id": "10"})
        SubElement(roar, "MxPatchRef")
    if with_plugin:
        plug = SubElement(devices, "PluginDevice", {"Id": "11"})
        _set_value(plug, "PluginDesc", "SyntheticPlugin")

    main_seq = SubElement(chain, "MainSequencer")
    clip_list = SubElement(main_seq, "ClipTimeable")
    arr = SubElement(clip_list, "ArrangerAutomation")
    events = SubElement(arr, "Events")
    midi_clip = SubElement(events, "MidiClip", {"Id": "0", "Time": "0"})
    notes = SubElement(midi_clip, "Notes")
    kt = SubElement(notes, "KeyTracks")
    key = SubElement(kt, "KeyTrack", {"Id": "0"})
    _set_value(key, "MidiKey", "60")
    note_events = SubElement(key, "Notes")
    SubElement(
        note_events,
        "MidiNoteEvent",
        {"Time": "0", "Duration": "0.25", "Velocity": "100", "IsEnabled": "true"},
    )

    audio = SubElement(tracks, "AudioTrack", {"Id": "2"})
    aname = SubElement(audio, "Name")
    _set_value(aname, "EffectiveName", "Drums")
    achain = SubElement(audio, "DeviceChain")
    routing = SubElement(achain, "AudioOutputRouting")
    _set_value(routing, "Target", "AudioOut/Main")

    aseq = SubElement(achain, "MainSequencer")
    aslot = SubElement(aseq, "ClipSlotList")
    slot = SubElement(aslot, "ClipSlot", {"Id": "3"})
    inner = SubElement(slot, "ClipSlot")
    val = SubElement(inner, "Value")
    aclip = SubElement(val, "AudioClip", {"Id": "0", "Time": "0"})
    sref = SubElement(aclip, "SampleRef")
    fref = SubElement(sref, "FileRef")
    _set_value(fref, "RelativePath", "Samples/Imported/kick_synthetic.wav")
    _set_value(fref, "Path", "C:/synthetic/Samples/Imported/kick_synthetic.wav")

    scenes = SubElement(live_set, "Scenes")
    SubElement(scenes, "Scene", {"Id": "0"})

    transport = SubElement(live_set, "Transport")
    tempo_el = SubElement(transport, "Tempo")
    _set_value(tempo_el, "Manual", tempo)

    buf = io.BytesIO()
    buf.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
    ElementTree(root).write(buf, encoding="utf-8", xml_declaration=False)
    return buf.getvalue()


def build_minimal_live11_xml() -> bytes:
    root = Element(
        "Ableton",
        {
            "MajorVersion": "5",
            "MinorVersion": "11.0_11300",
            "SchemaChangeCount": "3",
            "Creator": "Ableton Live 11.3.21",
            "Revision": "5ac24cad7c51ea0671d49e6b4885371f15b57c1e",
        },
    )
    live_set = SubElement(root, "LiveSet")
    tracks = SubElement(live_set, "Tracks")
    midi = SubElement(tracks, "MidiTrack", {"Id": "1"})
    name = SubElement(midi, "Name")
    _set_value(name, "EffectiveName", "Synth")
    chain = SubElement(midi, "DeviceChain")
    routing = SubElement(chain, "AudioOutputRouting")
    _set_value(routing, "Target", "AudioOut/Master")
    SubElement(live_set, "Scenes")
    transport = SubElement(live_set, "Transport")
    tempo_el = SubElement(transport, "Tempo")
    _set_value(tempo_el, "Manual", "120")
    buf = io.BytesIO()
    buf.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
    ElementTree(root).write(buf, encoding="utf-8", xml_declaration=False)
    return buf.getvalue()


def write_als(path: Path, xml_bytes: bytes) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as gz:
            gz.write(xml_bytes)
    return path
