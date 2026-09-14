# Ableton Live Set — format notes

## Container

An Ableton Live Set file (`.als`) is typically a single **gzip**-compressed stream
whose payload is **XML** (UTF-8).

Observed handling:

1. Read the file as binary.
2. Verify gzip magic (`1f 8b`).
3. Decompress with size / ratio limits (decompression-bomb protection).
4. Parse XML with a non-resolving parser (XXE protection).
5. Root element is `<Ableton ...>`.
6. Child `<LiveSet>` holds tracks, scenes, transport, etc.
7. Re-serialize XML and gzip into a **new** `.als`.

Unlike ZIP, gzip does not contain a multi-file archive; it wraps one logical file.

## Root `<Ableton>` attributes

Observed on Live 12 Demo / public tooling reports:

| Attribute | Example (Live 12.0.x) | Notes |
|-----------|------------------------|-------|
| `MajorVersion` | `5` | **Not** the marketing major (12). Internal document major. |
| `MinorVersion` | `12.0_12049` | Encodes marketing major/minor + build-ish token |
| `SchemaChangeCount` | `7` | Schema revision within that line |
| `Creator` | `Ableton Live 12.0` / `12.0.1` | Human-facing Live version string |
| `Revision` | hex git-like hash | Ableton build revision |

Observed Live 11.3.x (public `live_set` documentation):

| Attribute | Example |
|-----------|---------|
| `MajorVersion` | `5` |
| `MinorVersion` | `11.0_11300` |
| `SchemaChangeCount` | `3` |
| `Creator` | `Ableton Live 11.3.21` / `11.3.22` |
| `Revision` | e.g. `5ac24cad7c51ea0671d49e6b4885371f15b57c1e` |

**Do not invent** target `MinorVersion` / `SchemaChangeCount` / `Revision` values.
Only use values confirmed from authentic Sets or documented public evidence.

## Structural outline (simplified)

```text
Ableton
└── LiveSet
    ├── Tracks
    │   ├── MidiTrack / AudioTrack / GroupTrack / ReturnTrack / ...
    │   └── (Live 12) MainTrack  — Live 11 used Master-oriented naming in routing
    ├── Scenes
    ├── Transport
    ├── MasterTrack or MainTrack (version-dependent naming)
    └── ...
```

Device chains live under track `DeviceChain` nodes. Third-party plugins appear as
plugin device wrappers with opaque state blobs — preserve them; do not interpret.

Sample references appear under `SampleRef` / `FileRef` with `Path` and
`RelativePath` attributes. This tool must **not** open or rewrite sample files.

## Live 12 → 11 structural notes (evidence-based)

Public MIT `live_set` conversion (and author documentation) additionally:

- Removes Live 12-oriented nodes matching:
  `ContentLanes`, `ExpressionLanes`, `InstrumentMeld`, `Roar`, `MxPatchRef`, `Oversampling`
- Rewrites routing text `AudioOut/Main` → `AudioOut/Master`

These are **not** exhaustive. Newer point releases may introduce further schema.

## Security notes for parsers

Treat `.als` as untrusted input:

- Disable external entity resolution / DTD fetching
- Cap decompressed size and compression ratio
- Cap XML depth / element count for analysis paths
- Never execute Set contents or load plugins

## References

See `THIRD_PARTY.md`.
