"""Live 12 -> Live 11 transform profile."""

from __future__ import annotations

from xml.etree.ElementTree import ElementTree

from alsdowngrade.transforms.base import (
    Action,
    TransformResult,
    TransformRule,
    apply_root_metadata,
    remove_by_tag,
    replace_attr_and_text,
)
from alsdowngrade.version import resolve_target_fingerprint

# Explicit rules (clean-room reimplementation of publicly documented semantics)
LIVE12_TO_11_RULES: list[TransformRule] = [
    TransformRule(
        id="root_metadata_to_live11_3_21",
        source="12.x",
        target="11.x",
        selector="Ableton/@*",
        action=Action.MAP_ROOT_METADATA,
        reason="Older Live rejects newer root version fingerprints",
        evidence="mslinn/live_set modify_als; Ableton backward-compat docs",
        risk="medium",
        modes=["conservative", "compatible", "salvage"],
    ),
    TransformRule(
        id="audioout_main_to_master",
        source="12.x",
        target="11.x",
        selector="text:AudioOut/Main",
        action=Action.MAP_VALUE,
        reason="Live 12 routing uses Main; Live 11 uses Master",
        evidence="mslinn/live_set modify_als + author docs",
        risk="low",
        modes=["conservative", "compatible", "salvage"],
        params={"old": "AudioOut/Main", "new": "AudioOut/Master"},
    ),
    TransformRule(
        id="remove_content_lanes",
        source="12.x",
        target="11.x",
        selector="ContentLanes",
        action=Action.REMOVE,
        reason="Live 12 content/take-lane oriented structure",
        evidence="mslinn/live_set xpath //ContentLanes",
        risk="medium",
        modes=["compatible", "salvage"],
    ),
    TransformRule(
        id="remove_expression_lanes",
        source="12.x",
        target="11.x",
        selector="ExpressionLanes",
        action=Action.REMOVE,
        reason="Live 12 expression lanes",
        evidence="mslinn/live_set xpath //ExpressionLanes",
        risk="medium",
        modes=["compatible", "salvage"],
    ),
    TransformRule(
        id="remove_instrument_meld",
        source="12.x",
        target="11.x",
        selector="InstrumentMeld",
        action=Action.REMOVE,
        reason="Native Live 12 Meld device",
        evidence="mslinn/live_set xpath //InstrumentMeld",
        risk="high",
        modes=["compatible", "salvage"],
    ),
    TransformRule(
        id="remove_roar",
        source="12.x",
        target="11.x",
        selector="Roar",
        action=Action.REMOVE,
        reason="Native Live 12 Roar device",
        evidence="mslinn/live_set xpath //Roar",
        risk="high",
        modes=["compatible", "salvage"],
    ),
    TransformRule(
        id="remove_mx_patch_ref",
        source="12.x",
        target="11.x",
        selector="MxPatchRef",
        action=Action.REMOVE,
        reason="Max patch ref removed by public converter",
        evidence="mslinn/live_set xpath //MxPatchRef",
        risk="medium",
        modes=["compatible", "salvage"],
    ),
    TransformRule(
        id="remove_oversampling",
        source="12.x",
        target="11.x",
        selector="Oversampling",
        action=Action.REMOVE,
        reason="Oversampling node removed by public converter",
        evidence="mslinn/live_set xpath //Oversampling",
        risk="low",
        modes=["compatible", "salvage"],
    ),
]

CONSERVATIVE_BLOCKER_TAGS = {
    "InstrumentMeld",
    "Roar",
    "ContentLanes",
    "ExpressionLanes",
}


def apply_live12_to_11(
    tree: ElementTree, mode: str = "conservative", target: str = "11.2"
) -> TransformResult:
    mode = mode.lower()
    result = TransformResult()
    fp = resolve_target_fingerprint(target)
    mapping = {
        "MajorVersion": fp["MajorVersion"],
        "MinorVersion": fp["MinorVersion"],
        "SchemaChangeCount": fp["SchemaChangeCount"],
        "Creator": fp["Creator"],
    }
    if "Revision" in fp:
        mapping["Revision"] = fp["Revision"]

    for rule in LIVE12_TO_11_RULES:
        if mode not in rule.modes:
            continue
        if rule.action == Action.MAP_ROOT_METADATA:
            apply_root_metadata(tree, mapping)
            result.add(rule.id, "map_root_metadata", f"Set root to {fp['Creator']}")
        elif rule.action == Action.MAP_VALUE:
            old, new = rule.params["old"], rule.params["new"]
            n = replace_attr_and_text(tree, old, new)
            if n:
                result.add(rule.id, "map_value", f"{old} -> {new}", n)
        elif rule.action == Action.REMOVE:
            n = remove_by_tag(tree, rule.selector)
            if n:
                result.add(rule.id, "remove", f"Removed <{rule.selector}>", n)
                if rule.risk == "high":
                    result.warnings.append(
                        f"Removed {n}x <{rule.selector}> ({rule.reason})"
                    )
    return result
