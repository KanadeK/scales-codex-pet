# Release procedure

## Prepare

1. Confirm `CHANGELOG.md`, package version, and tag version agree.
2. Run the full local gate on Windows or Linux.
3. Run `python scripts/release_check.py --strict --json` from a clean commit.
4. Inspect the retained visual QA artifacts.
5. Verify Git identity and contributor history.

## Build

```bash
python -m build
python -m scales_pet package \
  --repo-root . \
  --version 0.1.0 \
  --output dist/scales-codex-pet-v0.1.0.zip \
  --manifest dist/release-manifest.json \
  --checksums dist/SHA256SUMS.txt \
  --json
```

Append wheel, source distribution, web atlas, and preview hashes to
`dist/SHA256SUMS.txt`. Verify every listed digest before upload.

## Publish

Push the exact release commit, wait for CI and Pages to pass, create the signed
or annotated `v0.1.0` tag, then let the tag workflow create the GitHub Release.
Do not publish assets from a different source state.

## Verify remotely

1. Inspect repository visibility and default branch.
2. Confirm all required GitHub Actions checks passed for the tagged SHA.
3. Confirm Pages serves the same saved source state.
4. Download all Release assets into a fresh directory.
5. Verify checksums and internal ZIP timestamps.
6. Validate both extracted atlases.
7. Inspect GitHub's contributors endpoint and commit history.

Only after these checks pass is the release complete.
