"""CLI entrypoint: inspect / analyze / diff / convert."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from alsdowngrade import __version__
from alsdowngrade.analyzer import analyze_for_target
from alsdowngrade.converter import convert_als
from alsdowngrade.diff import diff_als, format_diff
from alsdowngrade.gzip_io import load_als_xml_bytes
from alsdowngrade.parser import parse_als_xml
from alsdowngrade.report import format_conversion, format_inspect
from alsdowngrade.version import version_from_tree


def _load_tree(path: Path):
    _, xml = load_als_xml_bytes(path)
    return parse_als_xml(xml)


def cmd_inspect(args: argparse.Namespace) -> int:
    path = Path(args.path)
    tree = _load_tree(path)
    version = version_from_tree(tree)
    # Risk analysis is still Live-11-family oriented
    analysis = analyze_for_target(tree, target_major=11)
    print(format_inspect(str(path.resolve()), version, analysis))
    return 0


def cmd_analyze(args: argparse.Namespace) -> int:
    # Same as inspect for milestone 1, with explicit target emphasis
    return cmd_inspect(args)


def cmd_diff(args: argparse.Namespace) -> int:
    report = diff_als(args.left, args.right, normalize=args.normalize)
    print(format_diff(report))
    return 0


def cmd_convert(args: argparse.Namespace) -> int:
    report = convert_als(
        args.path,
        target=args.target,
        mode=args.mode,
        output=args.output,
        output_dir=args.output_dir,
    )
    print(format_conversion(report))
    if report.outcome.value in {"INVALID_INPUT", "REFUSED_UNSUPPORTED"}:
        return 2
    if report.output_path and any("FAIL" in m for m in report.validation_messages):
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="alsdowngrade",
        description=(
            "Local/offline Ableton Live Set downgrader. "
            "ORIGINAL .als FILES ARE NEVER MODIFIED."
        ),
    )
    p.add_argument("--version", action="version", version=f"alsdowngrade {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    insp = sub.add_parser("inspect", help="Inspect ALS metadata and structure (read-only)")
    insp.add_argument("path", help="Path to .als (read-only)")
    insp.add_argument(
        "--target",
        default="11.2",
        help="Target Live 11 point release for risk analysis (e.g. 11.2, 11.3, 11.1, 11.0)",
    )
    insp.set_defaults(func=cmd_inspect)

    ana = sub.add_parser("analyze", help="Compatibility / downgrade risk report")
    ana.add_argument("path", help="Path to .als (read-only)")
    ana.add_argument(
        "--target",
        default="11.2",
        help="Target Live 11 point release (e.g. 11.2, 11.3, 11.1, 11.0)",
    )
    ana.set_defaults(func=cmd_analyze)

    d = sub.add_parser("diff", help="Structural XML diff of two ALS files")
    d.add_argument("left", help="Older / left .als")
    d.add_argument("right", help="Newer / right .als")
    d.add_argument(
        "--normalize",
        action="store_true",
        help="Strip volatile Ids/Revision before comparing",
    )
    d.set_defaults(func=cmd_diff)

    c = sub.add_parser("convert", help="Write a NEW downgraded .als copy")
    c.add_argument("path", help="Source .als (never modified)")
    c.add_argument(
        "--target",
        default="11.2",
        help=(
            "Target Live 11 build fingerprint: 11.2 (default), 11.2.7, 11.2.11, "
            "11.3, 11.3.21, 11.1, 11.0"
        ),
    )
    c.add_argument(
        "--mode",
        choices=["conservative", "compatible", "salvage"],
        default="conservative",
        help="Conversion policy (default: conservative)",
    )
    c.add_argument(
        "--output",
        default=None,
        help="Explicit output .als path (still never overwrites silently)",
    )
    c.add_argument(
        "--output-dir",
        default="output",
        help="Directory for generated files (default: ./output)",
    )
    c.set_defaults(func=cmd_convert)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except Exception as exc:  # noqa: BLE001 - CLI boundary
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
