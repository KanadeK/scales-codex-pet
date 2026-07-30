# Research, novelty, and selection record

Snapshot date: **2026-07-30 (Asia/Shanghai)**. Search counts are point-in-time
evidence and may change after this repository is published.

## Decision

The selected character is **Scales**, the baby dragon from Blender Foundation's
open movie *Sintel*. Scales satisfies the three hard constraints:

1. Scales is an existing named animation character, not an invented look-alike.
2. Blender Foundation's Durian project and the four exact reference files
   provide a clear CC BY 3.0 reuse path with attribution.
3. No Scales or Sintel Codex pet was found in the local project inventory,
   GitHub repository search, or the leading community Codex-pet gallery.

The project does not promise a star count. Its discoverability thesis is
testable: it combines a recognizable open-movie character, unusually clear
commercially reusable attribution, a complete v2 atlas, a web-compatible v1
compiler, a live atlas-driven demo, and a submission path into an established
Codex-pet gallery.

## Local and historical duplicate check

The local `D:\我的\GitHub` inventory already contained or discussed these pet
directions and therefore excluded them:

- Baiyan;
- Feibi Jiubi;
- Kiki the Cyber Squirrel, including two Kiki repository variants;
- Pepper from *Pepper&Carrot*;
- the Miaocui Jiao cat.

Existing non-pet tools in the workspace were also reviewed by directory name.
This project does not reuse their product concepts. Its primary feature is a
dual-target Codex pet compiler and lifecycle replay tool.

## GitHub duplicate queries

The anonymous GitHub repository Search API returned `total_count: 0` for each
query:

```text
"Sintel" "Codex pet"
sintel-codex-pet
"Scales" "Codex pet"
"Morevna" "Codex pet"
```

The exact candidate was also checked through the public repository namespace
before publication. Repository search cannot prove that no private or
unindexed experiment exists, so the claim is deliberately scoped to public,
searchable evidence.

## Community gallery gap

[`legeling/awesome-codex-pet`](https://github.com/legeling/awesome-codex-pet)
had **490 stars**, **67 forks**, and **171 indexed pets** in the snapshot.
Its `pets.json` contained:

- 138 v1 pets and only 33 v2 pets;
- 44 anime-character pets;
- only 3 entries whose license string began with plain `CC BY`;
- zero case-insensitive matches for `Sintel` or `Scales`.

This makes a complete, provenance-checked CC BY v2 character adaptation a
genuine gap. The repository will include the metadata needed for a later
gallery submission without silently modifying that third-party project.

## Character and license evidence

Primary or canonical sources:

- [Sintel project sharing terms](https://durian.blender.org/sharing/) — Durian
  project results are CC BY 3.0; logos and associated trademarks are excluded.
- [Scales category on Wikimedia Commons](https://commons.wikimedia.org/wiki/Category:Scales_(Sintel))
  — identifies Scales as the fictional dragon in *Sintel* and groups the
  relevant media.
- [Baby Scales concept file](https://commons.wikimedia.org/wiki/File:Scale-baby.png)
  — David Revoy / Blender Foundation, CC BY 3.0.
- [Baby Scales wing study](https://commons.wikimedia.org/wiki/File:Scale-baby-wings.png)
  — David Revoy / Blender Foundation, CC BY 3.0.
- [Sintel film still](https://commons.wikimedia.org/wiki/File:Sintel-screenshot-2.jpg)
  — Blender Foundation, CC BY 3.0.

Every downloaded byte is pinned in `artwork/references/sources.json` and can be
verified offline with:

```bash
python -m scales_pet verify-provenance --json
```

## Product-format evidence

The current official Pets documentation distinguishes two surfaces:

- desktop-created custom pets are stored locally and selected after refreshing
  **Settings > Pets**;
- web custom uploads accept transparent PNG or WebP at exactly `1536x1872`
  and at most 20 MiB.

The hatch-pet v2 contract adds the local `1536x2288`, 8-by-11 atlas with
`spriteVersionNumber: 2`. This repository keeps the v2 atlas authoritative and
deterministically crops rows 0-8 into the official web upload dimensions,
pixel-checking that the two targets do not drift.

Official documentation: <https://learn.chatgpt.com/docs/pets>
