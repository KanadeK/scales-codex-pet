# Repair playbook

Start with machine-readable diagnosis:

```bash
scales-pet doctor --source pet --json
scales-pet validate pet --target desktop --strict --json
```

Do not delete an installed pet, backup, or lock until its purpose is known.

## Validation failures

### `required-cell-empty`

Regenerate or restore the complete semantic animation row. Reassemble the atlas
and rerun strict validation. Do not paint only the reported final cell.

### `unused-cell-populated`

Clear the full unused cell to transparent black. Re-encode losslessly and
validate both the authoritative atlas and web derivative. Row 0, column 6 is
not unused: it is the required desktop v2 neutral-look fallback and a compatible
optional cell in the exact-crop web derivative.

### `cell-edge-touch`

Reframe the complete row with safe padding. Strict mode treats this warning as
a release failure because edge contact is likely to clip in the host.

### `hidden-rgb`

Set RGB to zero wherever alpha is zero, then save as lossless WebP. This avoids
dark fringes and nondeterministic transparent bytes.

### `chroma-residue`

Visible pixels with alpha above 16 that remain near the generation key fail.
Return to the unprocessed completed atlas and run the approved edge-local
despill once, then inspect contact sheets again. Never rerun despill on the same
pixels; repeated global cleanup damages valid colors.

### `target-dimensions`

Desktop v2 must be `1536x2288`. Web upload must be `1536x1872`. Rebuild the web
asset from desktop:

```bash
scales-pet build-web --source pet \
  --output web-pet/scales-web-upload.webp --json
```

## Installation failures

### Active lock

If the lock is younger than 15 minutes, wait for the current install to finish.
If it is older, confirm no installer process is running, preserve a copy for
diagnosis, then remove only the exact lock reported by `doctor`.

### Installed hash drift

Run a dry run first:

```bash
scales-pet install --source pet --dry-run --json
```

Then reinstall. The drifted copy is moved into the Scales backup directory
before the validated source is swapped in.

### Broken new install

Restore the newest validated backup:

```bash
scales-pet rollback --json
```

Specify `--backup` only when intentionally selecting an older backup.

## Provenance failures

Do not update a SHA-256 merely to silence the gate. Compare the file with its
canonical description page, license, author, dimensions, and expected content.
Restore the pinned byte or document and review an intentional upstream change.

## Reproducibility failures

Build twice in separate directories. Compare file lists, order, permissions,
timestamps, manifest bytes, and archive paths. Time-dependent generated files
must not enter the release ZIP. All ZIP members must retain the fixed
`2020-01-01 00:00:00` timestamp.

## Site preview failures

Run:

```bash
python scripts/build_site.py --output build/site --json
python -m http.server 8000 --directory build/site
```

Open `http://localhost:8000`, not the raw HTML file. A `file:` URL blocks the
scenario fetch in some browsers. If the atlas fails to load, check
`build/site/site-data.json` and compare its hash with `pet/spritesheet.webp`.

## CI failures

Reproduce the failing job on the same Python version. Run the narrow failing
test, apply the smallest repair, then rerun the entire local gate. Never move a
release tag onto an unverified commit.
