# Third-party sources and licenses

This project is an independent implementation. References below are citations only
unless explicitly vendored with a compatible license.

## References (not vendored as code)

| Source | License / terms | Use in this project |
|--------|-----------------|---------------------|
| [Ableton Backward Compatibility](https://help.ableton.com/hc/en-us/articles/360000841004-Backward-Compatibility) | Ableton Help content | Documented product behavior |
| [mslinn/live_set](https://github.com/mslinn/live_set) | MIT | Public conversion semantics; **not** copied |
| [mslinn live_set article](https://www.mslinn.com/av_studio/live_set.html) | Author site | Technical notes on ALS + documented 12→11 steps |
| [owenbush/daw-schemas](https://github.com/owenbush/daw-schemas) | Check repo before copy | Structural schema notes; cite-only |
| [drj-io/abletron](https://github.com/drj-io/abletron) | MIT | Negative example: root-tag-only rewriter |
| Community ALS gzip/XML notes | Various | Format confirmation |

## Runtime dependencies

Milestone 1 uses the **Python standard library** only for the conversion engine
(`gzip`, `xml.etree.ElementTree`, `argparse`, `json`, `hashlib`, `re`, etc.).

Optional:

| Package | License | Purpose |
|---------|---------|---------|
| pytest | MIT | Tests |
| PySide6 | LGPL / commercial Qt | Future GUI only |

## Provenance of Live 11 target fingerprint

Target root attributes for Live 11.3.21 used in `schemas/versions.json` come from
public documentation of `live_set` / author notes describing authentic Live 11 Sets
and the Demo conversion path. Status remains **EXPERIMENTAL** until locally
Live-tested.
