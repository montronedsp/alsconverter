# Compatibility matrix

Statuses used by this project:

| Status | Meaning |
|--------|---------|
| RESEARCH | Investigating; no converter path |
| EXPERIMENTAL | Rules exist; based on public evidence / static tests |
| STATICALLY_VALIDATED | Automated validation layers pass on fixtures |
| LIVE_TESTED | Human opened result in real target Live |
| SUPPORTED | LIVE_TESTED + enough fixtures / confidence |

## Matrix

| Source → Target | Status | Notes |
|-----------------|--------|-------|
| Live 12.x → earlier Live 12.x (point) | RESEARCH | Ableton confirms point releases break opening; need authentic pairs |
| Live 12 → Live 11 | EXPERIMENTAL | Evidence-based rules from public MIT `live_set` path + static tests |
| Live 11 → Live 10 | RESEARCH | Not implemented |
| Live 10 → Live 9 | RESEARCH | Not implemented |

## Live 12 → Live 11 (current)

**Profile id:** `live12_to_live11`

**Target fingerprints (documented):** selectable Live 11 point releases in `schemas/versions.json`.

Default target is **Live 11.2.11** (`MinorVersion=11.0_11202`, `SchemaChangeCount=17`) because Ableton point releases are not cross-compatible: a Set stamped as 11.3 will not open in 11.2.

Also available: `11.2.7`, `11.3.21`, `11.1`, `11.0.12`.

**Known transforms:**

- Remap root version metadata to documented Live 11 fingerprint
- Remove known Live 12-oriented nodes: `ContentLanes`, `ExpressionLanes`,
  `InstrumentMeld`, `Roar`, `MxPatchRef`, `Oversampling`
- Normalize `AudioOut/Main` → `AudioOut/Master`

**Known unsupported / high risk:**

- Native Live 12 devices (e.g. Roar, Meld) — removed in Compatible/Salvage; refused in Conservative if present
- Structures we have not differentially confirmed for later 12.x point releases
- Max for Live devices — preserved but flagged UNKNOWN
- Third-party plugins — state preserved; presence on destination machine not guaranteed

**Mandatory disclaimer:** Static XML validation ≠ “opens in Live 11”.
Real Ableton Live 11 opening test: **NOT YET VERIFIED** until you run the checklist
in `TESTING.md`.

## Do not invent metadata

If a target fingerprint is not confirmed, fields remain `UNKNOWN` and conversion
to that exact point release is refused or remains RESEARCH.
