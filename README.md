# Ableton Live Set Downgrader

Local/offline tool that creates a **new downgraded copy** of an Ableton Live `.als` Set
intended for an older Live version.

**Original files are never modified.**

Open source (MIT): [github.com/montronedsp/alsconverter](https://github.com/montronedsp/alsconverter)

## Privacy

This project does **not** collect any data. Conversion runs entirely on your machine.
There is no account, telemetry, analytics, or cloud upload in the CLI, GUI, or
in-browser tool.

## Status (Milestone 1)

| Path | Status |
|------|--------|
| Live 12 → Live 11 | **EXPERIMENTAL** (static validation + public evidence) |
| Live 12.x → earlier 12.x | RESEARCH |
| Live 11 → 10 / 10 → 9 | RESEARCH (not implemented) |

## Safety

- Never overwrites the source `.als`
- Writes only to `output/` (or an explicitly chosen destination)
- Never silently overwrites an existing destination
- Never launches Ableton, touches samples, plugins, or preferences
- Treats every real Ableton project as read-only

## Install

```bash
cd ableton-downgrader   # or this repository root
python -m pip install -e ".[dev]"
```

## Commands

```bash
# Inspect a Set (read-only)
alsdowngrade inspect "path/to/Session.als"

# Compatibility / risk report
alsdowngrade analyze "path/to/Session.als" --target 11.2

# Structural XML diff
alsdowngrade diff "older.als" "newer.als"
alsdowngrade diff "older.als" "newer.als" --normalize

# Convert Live 12 → Live 11.2 (default; use --target for other 11.x builds)
alsdowngrade convert "path/to/Session.als" --target 11.2

# Other Live 11 point releases
alsdowngrade convert "Session.als" --target 11.2.7 --mode compatible
alsdowngrade convert "Session.als" --target 11.3 --mode compatible
alsdowngrade convert "Session.als" --target 11.1 --mode compatible
alsdowngrade convert "Session.als" --target 11.0 --mode compatible
```

## Windows GUI

```bash
python -m pip install -e .
alsdowngrade-gui
```

Build a portable Windows folder (PyInstaller):

```powershell
powershell -File scripts/build-windows.ps1
```

Output: `dist/ALSConverter/ALSConverter.exe`

Prebuilt Windows release: [v0.1.0](https://github.com/montronedsp/alsconverter/releases/tag/v0.1.0)

**NO WARRANTY / NO GUARANTEE.** Provided as-is. Converted Sets may fail to open or lose features. Keep backups. Not affiliated with Ableton AG.

Example output name:

`Session.als` → `Session_Live11_2_11_downgraded.als`

## What this is not

This is **not** a header-only `Creator` string patcher. Conversion uses an explicit
transform-rule engine (metadata remapping, known Live-12-only structure handling,
routing path normalization) with validation layers. See `docs/`.

## License

MIT. Third-party references are documented in `docs/THIRD_PARTY.md`.
