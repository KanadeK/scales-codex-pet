# Acceptance contract

## Supported environments

- Python 3.11, 3.12, and 3.13
- Windows and Linux for validation, replay, packaging, and tests
- Codex desktop for the local v2 pet
- ChatGPT web custom pet upload for the nine-row derivative

## Local gate

Install development dependencies, then run:

```bash
python -m pip install -e ".[dev]"
python scripts/release_check.py --json
python -m ruff check .
python -m mypy src
python -m coverage run -m unittest discover -s tests -t . -v
python -m coverage report
python -m build
```

Expected outcomes:

- every command exits `0`;
- release check reports `"ok": true`;
- desktop validation reports 74 populated required cells and 14 empty unused
  cells;
- web validation reports 57 populated required cells and 14 empty unused cells;
- cross-target pixel comparison is true;
- scenario replay produces more than zero real frames;
- two deliberately separate package builds have the same SHA-256;
- all ZIP entries use `2020-01-01 00:00:00`;
- coverage is at least 85 percent;
- wheel and source distribution exist under `dist/`.

## Strict repository gate

After creating the release commit and configuring `origin`:

```bash
python scripts/release_check.py --strict --json
git status --short
git shortlog -sne HEAD
git log --format=fuller
```

Expected outcomes:

- the worktree is clean;
- `origin` resolves to `github.com/KanadeK/scales-codex-pet` in HTTPS or SSH
  form, with or without the optional `.git` suffix;
- author and committer identities are populated;
- history contains no additional-author trailers;
- `git shortlog` lists only intended contributors.

## Public release gate

Local success is not public delivery. Verify all of the following:

```bash
gh auth status
gh repo view KanadeK/scales-codex-pet --json nameWithOwner,url,visibility,defaultBranchRef
gh run list --repo KanadeK/scales-codex-pet --limit 10
gh release view v0.1.0 --repo KanadeK/scales-codex-pet
gh api repos/KanadeK/scales-codex-pet/contributors
```

Then download the published archive and checksum file into a new directory,
verify SHA-256, inspect ZIP timestamps, and run both strict atlas validators
against the extracted release. The Pages URL must load the real atlas and the
scenario button must complete without a preview error.

## Visual acceptance

The retained QA bundle must include:

- canonical base sprite;
- standard-row contact sheet;
- standard-row animation GIFs;
- direction contact sheet;
- direction sweep GIF;
- full-atlas preview;
- blind direction semantic reports;
- final validator JSON.

Identity, scale, outline, palette, grounding, and gaze mechanics must stay
continuous across complete rows. A numerically valid atlas can still fail this
visual gate.
