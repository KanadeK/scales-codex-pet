# Visual QA evidence

These artifacts document the accepted v2 pet rather than serving as source
frames for later cosmetic edits.

- `contact-sheet.png` and `scales-overview.png` show all 11 atlas rows.
- `look-directions.png` shows the neutral frame and all 16 labeled look
  directions at normal and zoomed size.
- `direction-blind-*.json` contains the three isolated classifications,
  strict-majority consensus, hidden answer key, and validator result.
- `direction-semantics.json` records every expected direction with visible
  horizontal and vertical evidence.
- `look-continuity.json`, `chroma-despill-extended.json`, and
  `validation-extended.json` retain deterministic measurements.
- `final-visual-qa.json` records the independent 11-row visual acceptance.
- `run-summary.json` links the portable release package to every retained
  deterministic and visual gate.
- `previews/` contains the nine standard-state GIF loops.
- `canonical-base.png` is the approved identity reference, and
  `look-direction-sweep.gif` animates all 16 v2 look cells in degree order.

The final blind validation has `ok: true`; both cardinal pairs pass. The
subtle 022.5-degree horizontal cue and two continuity metric outliers are
preserved as reviewed warnings, not hidden or silently discarded.
