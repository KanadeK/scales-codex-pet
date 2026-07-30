# Contributing

Thank you for helping Scales stay recognizable, safe to install, and easy to
audit.

## Development setup

```bash
python -m pip install -e ".[dev]"
python -m unittest discover -s tests -t . -v
python -m ruff check .
python -m mypy src
```

## Change rules

- Preserve the CC BY 3.0 attribution and source records for all visual inputs.
- Add a pinned canonical source and change note before introducing new visual
  reference material.
- Replace and review complete animation rows. Do not repair only one final
  atlas cell.
- Keep `pet/spritesheet.webp` authoritative and compile the web asset from it.
- Add tests for behavior changes and a repair message for new failure modes.
- Preserve transactional installation and backup recovery.
- Do not include generated caches, local Codex state, credentials, or hatch
  work directories.

## Before opening a pull request

Run every command in `docs/ACCEPTANCE.md`. Describe the user-visible behavior,
test evidence, asset provenance changes, and recovery impact. Include contact
sheets or GIF evidence for visual changes.
