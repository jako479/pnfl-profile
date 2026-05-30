# pnfl-profile — Status

**Status: Initial Implementation Complete**

PNFL league-rule wrapper for `fbpro98-profile`. Provides save-time validation and a queryable list of rule violations for any `.prf` coaching profile.

## Implemented

- `PnflProfile` composition wrapper — pairs a `Profile` with a `PnflRules` instance; exposes `from_file`, `from_bytes`, `validate`, and `save`.
- `PNFL_RULES` rule set — see [RULES.md](RULES.md) for the full list. Covers universal (audibles unchecked), offensive (QB sub 75/80 + per-situation allowed/mandatory matrix), defensive (3rd-down mandatory `PS` / `PM` / `PL`), the category-count minimum (3 standard, lowered to 2 within own 5 or when ≤5:00 remain), and the 4th-down kick exemption.
- `validate_profile` — pure-function validator yielding `tuple[Violation, ...]`; one violation per rule breach with optional `situation_number`.
- `save` — emits per-violation `warnings.warn(..., PnflRuleWarning)` calls (prefixed with `[situation N]` when present), writes via `fbpro98-profile`, and returns the violation tuple. PNFL violations never block the write — callers that want a strict gate read the returned tuple. Apps that want every violation surfaced every save install `warnings.simplefilter("always", PnflRuleWarning)` at entry.

## Not yet covered

- PAT logic, field-goal range, stop-clock, and sub-percentage rules — not present in the rule source.
- `pnfl` CLI subcommand integration — none yet; this package is library-only.
