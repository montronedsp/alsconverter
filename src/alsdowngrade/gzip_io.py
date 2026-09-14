"""Safe gzip read/write for .als containers.

Never modifies the source path. Decompression limits protect against bombs.
"""

from __future__ import annotations

import gzip
import io
import os
from pathlib import Path

GZIP_MAGIC = b"\x1f\x8b"

# Hard caps - .als Sets are large but pathological streams must fail closed.
DEFAULT_MAX_COMPRESSED_BYTES = 512 * 1024 * 1024  # 512 MiB compressed
DEFAULT_MAX_DECOMPRESSED_BYTES = 1024 * 1024 * 1024  # 1 GiB XML
DEFAULT_MAX_RATIO = 200  # decompressed / compressed


class AlsIOError(ValueError):
    """Invalid or unsafe ALS container."""


def read_bytes_limited(path: Path, max_bytes: int = DEFAULT_MAX_COMPRESSED_BYTES) -> bytes:
    path = Path(path)
    if not path.is_file():
        raise AlsIOError(f"Not a file: {path}")
    size = path.stat().st_size
    if size > max_bytes:
        raise AlsIOError(f"Compressed file exceeds limit ({size} > {max_bytes} bytes)")
    data = path.read_bytes()
    if len(data) > max_bytes:
        raise AlsIOError("Compressed file exceeds limit after read")
    return data


def decompress_als(
    data: bytes,
    *,
    max_decompressed: int = DEFAULT_MAX_DECOMPRESSED_BYTES,
    max_ratio: int = DEFAULT_MAX_RATIO,
) -> bytes:
    if len(data) < 2 or data[:2] != GZIP_MAGIC:
        raise AlsIOError("Not a gzip-compressed .als (missing gzip magic)")
    compressed_len = max(len(data), 1)
    out = io.BytesIO()
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(data), mode="rb") as gz:
            while True:
                chunk = gz.read(1024 * 1024)
                if not chunk:
                    break
                if out.tell() + len(chunk) > max_decompressed:
                    raise AlsIOError("Decompressed XML exceeds size limit")
                out.write(chunk)
                if out.tell() / compressed_len > max_ratio:
                    raise AlsIOError("Suspicious compression ratio (possible zip bomb)")
    except AlsIOError:
        raise
    except OSError as exc:
        raise AlsIOError(f"gzip decompression failed: {exc}") from exc
    return out.getvalue()


def compress_als(xml_bytes: bytes) -> bytes:
    buf = io.BytesIO()
    # mtime=0 for deterministic tests; Ableton tolerates standard gzip headers.
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as gz:
        gz.write(xml_bytes)
    return buf.getvalue()


def load_als_xml_bytes(path: Path | str) -> tuple[bytes, bytes]:
    """Return (compressed_bytes, xml_bytes). Source file is only read."""
    compressed = read_bytes_limited(Path(path))
    xml_bytes = decompress_als(compressed)
    return compressed, xml_bytes


def unique_output_path(desired: Path) -> Path:
    """Never overwrite: add _1, _2, ... before suffix if needed."""
    desired = Path(desired)
    if not desired.exists():
        return desired
    stem = desired.stem
    suffix = desired.suffix
    parent = desired.parent
    n = 1
    while True:
        candidate = parent / f"{stem}_{n}{suffix}"
        if not candidate.exists():
            return candidate
        n += 1


def default_output_path(source: Path, target_label: str, output_dir: Path) -> Path:
    source = Path(source)
    safe_stem = Path(source.name).stem  # basename only - no traversal
    # Strip any residual path segments from malicious names
    safe_stem = os.path.basename(safe_stem)
    if not safe_stem or safe_stem in {".", ".."}:
        safe_stem = "set"
    name = f"{safe_stem}_Live{target_label.replace('.', '_')}_downgraded.als"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    return unique_output_path(output_dir / name)


def write_new_als(path: Path, compressed: bytes) -> Path:
    path = Path(path)
    if path.exists():
        path = unique_output_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Write via temp then replace within same directory only after full write
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        tmp.write_bytes(compressed)
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
    return path
