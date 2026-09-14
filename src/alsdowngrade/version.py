"""Compatibility / version model for Ableton Sets."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from xml.etree.ElementTree import Element, ElementTree

CREATOR_RE = re.compile(
    r"Ableton Live\s+(\d+)(?:\.(\d+))?(?:\.(\d+))?",
    re.IGNORECASE,
)
MINOR_RE = re.compile(r"^(\d+)\.(\d+)_(\d+)$")


@dataclass(frozen=True)
class SetVersion:
    creator: str
    major_version: str  # document MajorVersion attribute
    minor_version: str
    schema_change_count: str
    revision: str
    marketing_major: int | None
    marketing_minor: int | None
    marketing_patch: int | None
    minor_token_major: int | None
    minor_token_minor: int | None
    minor_build_token: str | None

    @property
    def label(self) -> str:
        if self.marketing_major is not None:
            parts = [str(self.marketing_major)]
            if self.marketing_minor is not None:
                parts.append(str(self.marketing_minor))
                if self.marketing_patch is not None:
                    parts.append(str(self.marketing_patch))
            return ".".join(parts)
        if self.minor_token_major is not None:
            return f"{self.minor_token_major}.{self.minor_token_minor or 0}"
        return "UNKNOWN"


def _parse_creator(creator: str) -> tuple[int | None, int | None, int | None]:
    m = CREATOR_RE.search(creator or "")
    if not m:
        return None, None, None
    major = int(m.group(1))
    minor = int(m.group(2)) if m.group(2) is not None else None
    patch = int(m.group(3)) if m.group(3) is not None else None
    return major, minor, patch


def _parse_minor(minor: str) -> tuple[int | None, int | None, str | None]:
    m = MINOR_RE.match((minor or "").strip())
    if not m:
        return None, None, None
    return int(m.group(1)), int(m.group(2)), m.group(3)


def parse_set_version(root: Element) -> SetVersion:
    creator = root.attrib.get("Creator", "")
    major_version = root.attrib.get("MajorVersion", "")
    minor_version = root.attrib.get("MinorVersion", "")
    schema = root.attrib.get("SchemaChangeCount", "")
    revision = root.attrib.get("Revision", "")
    mmaj, mmin, mpat = _parse_creator(creator)
    tmaj, tmin, tbuild = _parse_minor(minor_version)
    # Prefer MinorVersion marketing major when Creator is missing/odd
    if mmaj is None and tmaj is not None:
        mmaj, mmin = tmaj, tmin
    return SetVersion(
        creator=creator,
        major_version=major_version,
        minor_version=minor_version,
        schema_change_count=schema,
        revision=revision,
        marketing_major=mmaj,
        marketing_minor=mmin,
        marketing_patch=mpat,
        minor_token_major=tmaj,
        minor_token_minor=tmin,
        minor_build_token=tbuild,
    )


def version_from_tree(tree: ElementTree) -> SetVersion:
    return parse_set_version(tree.getroot())


def load_versions_db() -> dict:
    path = resources.files("alsdowngrade").joinpath("schemas/versions.json")
    return json.loads(path.read_text(encoding="utf-8"))


def load_profiles() -> dict:
    path = resources.files("alsdowngrade").joinpath(
        "schemas/compatibility_rules/profiles.json"
    )
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_target_fingerprint(target: str) -> dict:
    """Map CLI target like '11.2' / '11.3' to a documented fingerprint or raise."""
    db = load_versions_db()
    fingerprints = db["fingerprints"]
    aliases = db.get("target_aliases", {})
    t = target.strip().lower()
    if t.startswith("live"):
        t = t[4:].lstrip()
    key = aliases.get(t)
    if key is None or key not in fingerprints:
        supported = ", ".join(sorted(aliases.keys()))
        raise ValueError(
            f"Target '{target}' is not implemented or lacks confirmed fingerprint. "
            f"Supported targets: {supported}"
        )
    fp = fingerprints[key]
    label = fp.get("id") or fp.get("label") or t
    result = {
        "target_label": str(label),
        "profile": "live12_to_live11",
        "fingerprint_id": key,
        "MajorVersion": fp["MajorVersion"],
        "MinorVersion": fp["MinorVersion"],
        "SchemaChangeCount": fp["SchemaChangeCount"],
        "Creator": fp["Creator"],
        "status": fp["status"],
        "source": fp["source"],
    }
    # Only set Revision when documented (empty string means omit / clear)
    if "Revision" in fp and fp["Revision"]:
        result["Revision"] = fp["Revision"]
    elif "Revision" in fp and fp["Revision"] == "":
        result["Revision"] = ""
    return result


def list_target_aliases() -> list[str]:
    db = load_versions_db()
    return sorted(db.get("target_aliases", {}).keys())


def is_live12_family(version: SetVersion) -> bool:
    return (version.marketing_major == 12) or (version.minor_token_major == 12)


def is_live11_family(version: SetVersion) -> bool:
    return (version.marketing_major == 11) or (version.minor_token_major == 11)


def project_root_from_cwd() -> Path:
    return Path.cwd()
