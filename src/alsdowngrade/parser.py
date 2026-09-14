"""XML parse/serialize with XXE and depth protections."""

from __future__ import annotations

import io
import re
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import Element

# ElementTree does not resolve external entities by default in modern Python,
# but we still reject DOCTYPE / ENTITY declarations defensively.
_DOCTYPE_RE = re.compile(rb"<!DOCTYPE", re.IGNORECASE)
_ENTITY_RE = re.compile(rb"<!ENTITY", re.IGNORECASE)

DEFAULT_MAX_DEPTH = 256
DEFAULT_MAX_ELEMENTS = 2_000_000


class AlsParseError(ValueError):
    """Malformed or unsafe ALS XML."""


def _reject_xxe(xml_bytes: bytes) -> None:
    # Scan a prefix + whole doc for entity expansion vectors
    if _DOCTYPE_RE.search(xml_bytes) or _ENTITY_RE.search(xml_bytes):
        raise AlsParseError("XML contains DOCTYPE/ENTITY (blocked for XXE safety)")


def _check_depth_and_count(
    root: Element,
    *,
    max_depth: int = DEFAULT_MAX_DEPTH,
    max_elements: int = DEFAULT_MAX_ELEMENTS,
) -> None:
    count = 0
    stack: list[tuple[Element, int]] = [(root, 1)]
    while stack:
        el, depth = stack.pop()
        count += 1
        if count > max_elements:
            raise AlsParseError("XML exceeds element count limit")
        if depth > max_depth:
            raise AlsParseError("XML exceeds depth limit")
        for child in list(el):
            stack.append((child, depth + 1))


def parse_als_xml(xml_bytes: bytes) -> ET.ElementTree:
    if not xml_bytes or not xml_bytes.strip():
        raise AlsParseError("Empty XML")
    _reject_xxe(xml_bytes)
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        raise AlsParseError(f"XML parse failed: {exc}") from exc
    if root.tag != "Ableton":
        raise AlsParseError(f"Expected root <Ableton>, got <{root.tag}>")
    _check_depth_and_count(root)
    live_set = root.find("LiveSet")
    if live_set is None:
        raise AlsParseError("Missing required <LiveSet> child")
    return ET.ElementTree(root)


def serialize_als_xml(tree: ET.ElementTree) -> bytes:
    root = tree.getroot()
    # Ableton files typically declare UTF-8 XML header.
    buf = io.BytesIO()
    buf.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
    ET.ElementTree(root).write(buf, encoding="utf-8", xml_declaration=False)
    return buf.getvalue()


def get_root(tree: ET.ElementTree) -> Element:
    root = tree.getroot()
    if root is None or root.tag != "Ableton":
        raise AlsParseError("Invalid Ableton root")
    return root
