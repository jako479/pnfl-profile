# pnfl-profile — Status

**Status: Initial Implementation Complete**

PNFL league-rule wrapper for `fbpro98-profile`. Provides save-time validation and a queryable list of rule violations for any `.prf` coaching profile.

## Implemented

- `PnflProfile` composition wrapper — pairs a `Profile` with a `PnflRules` instance; exposes `from_file`, `from_bytes`, `validate`, and `save`.
- `PNFL_RULES` rule set — universal (audibles unchecked), offensive (QB sub 75/80 + per-situation allowed/mandatory matrix), defensive (3rd-down mandatory `PS` / `PM` / `PL` cells), and the 3-category minimum (relaxed to 2 within own 5-yard line) for both sides.
- `validate_profile` — pure-function validator yielding `tuple[Violation, ...]`; one violation per rule breach with optional `situation_number`.
- `save` — validates first, raises `PnflRuleError(violations)` on any violation, otherwise writes via `fbpro98-profile`.

## Not yet covered

- PAT logic, field-goal range, stop-clock, and sub-percentage rules — not present in the rule source.
- 4th-down play-category rules — not present in the rule source.
- Punt/FG one-category-allowed shortcut — not modeled.
- `pnfl` CLI subcommand integration — none yet; this package is library-only.
