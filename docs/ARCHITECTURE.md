# Architecture and invariants

## System boundary

The repository treats `pet/spritesheet.webp` and `pet/pet.json` as the
authoritative product. Every other runtime artifact is either a verified view
of that product or a deterministic derivative.

| Component | Input | Real output | Failure behavior |
| --- | --- | --- | --- |
| Validator | pet directory or atlas | structured report | nonzero exit with repair text |
| Web compiler | validated v2 atlas | nine-row WebP | removes invalid partial output |
| Scenario renderer | v2 atlas and JSON events | animated GIF | rejects bad state and size |
| Installer | validated pet directory | local Codex pet | restores prior backup on failure |
| Doctor | source and Codex home | hash, lock, backup diagnosis | reports corrupt files without crashing |
| Packager | validated dual targets | deterministic ZIP, manifest, checksums | emits no release on failed validation |
| Site builder | validated dual targets | static pet lab | refuses missing or invalid assets |

## Sprite contracts

Both targets use 8 columns of `192x208` cells.

Desktop v2 is `1536x2288` with 11 rows:

| Row | State | Required frames |
| ---: | --- | ---: |
| 0 | idle + neutral look fallback | 6 + column 6 neutral |
| 1 | running-right | 8 |
| 2 | running-left | 8 |
| 3 | waving | 4 |
| 4 | jumping | 5 |
| 5 | failed | 8 |
| 6 | waiting | 6 |
| 7 | running | 6 |
| 8 | review | 6 |
| 9 | look 000 through 157.5 | 8 |
| 10 | look 180 through 337.5 | 8 |

Web v1 is `1536x1872` and contains rows 0 through 8. It is never edited
independently. The desktop neutral look fallback at row 0, column 6 is retained
as a compatible optional cell so the web file remains an exact desktop crop.

## Release invariants

1. Every required cell has visible alpha, including the desktop v2 neutral
   look fallback at row 0, column 6.
2. Every unused cell is transparent black.
3. No required sprite touches a cell edge.
4. Fully transparent pixels have zero RGB.
5. Visible generation-key residue is zero.
6. Desktop manifest declares `spriteVersionNumber: 2`.
7. Web pixels equal the corresponding desktop crop exactly.
8. Every upstream reference matches its pinned SHA-256.
9. The same source state produces the same ZIP bytes.
10. Installation never destroys the previous pet during a failed swap.

## Trust boundaries

- JSON scenarios are untrusted and bounded to 100 events, 1000 expanded frames,
  defined states, and finite timing ranges.
- Manifest sprite paths must remain within the pet directory.
- Install destinations are derived only from a supplied Codex home or the
  documented default.
- Backup selections must be descendants of the Scales backup root.
- Release archive names are repository-owned constants, not user input.
- Site output must be a dedicated directory inside the repository.

## Why Python and a dependency-free site

Pillow provides deterministic image inspection and lossless WebP operations on
all supported CI platforms. The browser preview uses native canvas and static
files so the published demo has no package-manager runtime, no remote script
dependency, and no fake product screenshot.
