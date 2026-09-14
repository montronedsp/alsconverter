from __future__ import annotations

from pathlib import Path

from alsdowngrade.cli import main


def test_cli_inspect(live12_minimal: Path, capsys) -> None:
    assert main(["inspect", str(live12_minimal)]) == 0
    out = capsys.readouterr().out
    assert "Ableton Live 12" in out
    assert "MajorVersion" in out


def test_cli_convert(live12_minimal: Path, tmp_path: Path, capsys) -> None:
    code = main(
        [
            "convert",
            str(live12_minimal),
            "--target",
            "11.2",
            "--output-dir",
            str(tmp_path),
        ]
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "NOT YET VERIFIED" in out
    assert "ORIGINAL FILE IS NEVER MODIFIED" in out
    assert list(tmp_path.glob("*_Live11_2_11_downgraded.als")) or list(
        tmp_path.glob("*_downgraded.als")
    )