# Testing guide

## Automated tests

```bash
python -m pip install -e ".[dev]"
pytest -q
```

Fixtures under `tests/fixtures/` are **synthetic** gzip XML Sets. They must never
contain commercial session audio or private paths.

## Safety checks during development

1. Source `.als` byte-identical before/after any convert command
2. Output only under `output/` or an explicit `--output` path
3. Existing destinations get a unique suffix — no silent overwrite

## Layered validation (what the tool already runs)

1. Container: gzip magic, decompress, size limits
2. XML: parse, single Ableton root, LiveSet present
3. Structural: track/clip/note/device count deltas
4. Target schema: leftover known source-only markers
5. Round-trip: gzip→XML→serialize→gzip→reopen→parse
6. Real Ableton: **human only**

## Manual Live verification checklist (required for LIVE_TESTED)

Do **not** let automation launch Ableton.

1. Convert with this tool into `output/`
2. Copy **only** the new `.als` into a disposable test project folder (optional)
3. Open the **converted** file in the target Live version (e.g. Live 11)
4. Confirm Live does not error on load
5. Check track count/names, tempo, clips, MIDI notes, plugin instances
6. Play back and listen for missing devices / silence from removed Live 12 devices
7. Record results (pass/fail + Live exact version) without committing private Sets
8. Only then may project status move toward `LIVE_TESTED`
