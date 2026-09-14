"""Transform rule primitives."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from xml.etree.ElementTree import ElementTree


class Action(str, Enum):
    REMOVE = "remove"
    MAP_ROOT_METADATA = "map_root_metadata"
    MAP_VALUE = "map_value"
    FLAG = "flag"
    LEAVE = "leave"


@dataclass
class TransformRule:
    id: str
    source: str
    target: str
    selector: str
    action: Action
    reason: str
    evidence: str
    risk: str
    modes: list[str] = field(default_factory=lambda: ["compatible"])
    params: dict = field(default_factory=dict)


@dataclass
class TransformEvent:
    rule_id: str
    action: str
    detail: str
    count: int = 1


@dataclass
class TransformResult:
    events: list[TransformEvent] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def add(self, rule_id: str, action: str, detail: str, count: int = 1) -> None:
        self.events.append(TransformEvent(rule_id, action, detail, count))


def remove_by_tag(tree: ElementTree, tag: str) -> int:
    """Remove all elements with the given tag name anywhere in the tree."""
    root = tree.getroot()
    removed = 0
    changed = True
    while changed:
        changed = False
        for parent in list(root.iter()):
            for child in list(parent):
                if child.tag == tag:
                    parent.remove(child)
                    removed += 1
                    changed = True
    return removed


def apply_root_metadata(tree: ElementTree, mapping: dict[str, str]) -> None:
    root = tree.getroot()
    for key, value in mapping.items():
        root.set(key, value)


def replace_attr_and_text(tree: ElementTree, old: str, new: str) -> int:
    count = 0
    for el in tree.getroot().iter():
        for attr, val in list(el.attrib.items()):
            if old in val:
                el.set(attr, val.replace(old, new))
                count += 1
        if el.text and old in el.text:
            el.text = el.text.replace(old, new)
            count += 1
        if el.tail and old in el.tail:
            el.tail = el.tail.replace(old, new)
            count += 1
    return count
