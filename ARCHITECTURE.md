# pnfl-profile — Architecture

Library owning the PNFL coaching-profile rule set; pairs a `Profile` from `fbpro98-profile` with `PnflRules` for rule-aware I/O.

## Module layout

```
src/pnfl_profile/
├── __init__.py    # public API + re-exports
├── model.py       # PnflProfile, Violation, PnflRuleWarning
├── rules.py       # SituationRule, PnflRules, PNFL_RULES, play-category constants
└── validators.py  # validate_profile + per-rule helpers
```

## Composition, not inheritance

`PnflProfile` wraps a `Profile` + `PnflRules` — does not inherit. Subclassing would violate Liskov: code written against `Profile` would silently see new behavior from a `PnflProfile`.

Property forwarders (`profile_type`, `substitutions`, `situations`, `pat_situations`, `field_goal_range`, `use_audibles`, `is_offense`, `is_defense`, `stop_clock_situations`) give the wrapper a `Profile`-shaped API. Re-exports of `fbpro98-profile` value types (`Profile`, `Situation`, etc.) and I/O (`read_profile`, `parse_profile`, `write_profile`, `InvalidProfileError`, `UnsupportedProfileError`) mean downstream consumers depend only on `pnfl-profile`.

## Rule data

`PNFL_RULES` is a frozen `PnflRules` in [rules.py](src/pnfl_profile/rules.py). Per-situation rules key on `(Down, YardsToGo, FieldPosition)`; point spread isn't a rule input; time is a gate. Field position is offense-perspective in `.prf`, so the "own 5-yard line" exception resolves to `INSIDE_OFF_5` on offense, `INSIDE_DEF_5` on defense.

Category-count thresholds:

- Standard: 3 categories with weight > 0.
- 2 when `MinutesRemaining != OVER_FIVE` (≤5:00 remaining) — any field, any down.
- 2 when `MinutesRemaining == OVER_FIVE` and field is in the relaxed set (`INSIDE_OFF_5` / `INSIDE_DEF_5`).
- Waived when down is 4th and `PUNT` or `FIELD_GOAL_PAT` has weight > 0.

Matrix rules (allowed/mandatory category sets) fire only when `MinutesRemaining == OVER_FIVE`.

## Validation contract

`validate_profile(profile, rules)` returns one `Violation` per breach. `PnflProfile.save(path)` calls it, emits one `warnings.warn(..., PnflRuleWarning)` per violation (prefixed `[situation N]` when present), and writes via `fbpro98-profile`'s `write_profile` **regardless**. Returns the violation tuple. Library installs no `warnings` filter; apps install `warnings.simplefilter("always", PnflRuleWarning)` at entry. Mirrors `pnfl-gameplan`'s warn-and-persist policy.

## Not in scope

- File format parsing/writing — `fbpro98-profile`.
- PAT logic, FG range, stop-clock, sub-percent rules — not in the league rules thread; no validators yet.
- Gameplan validation — separate package.

## Testing

- [tests/test_validators.py](tests/test_validators.py) — every rule against a compliant baseline mutated to fire only that rule.
- [tests/test_pnfl_profile.py](tests/test_pnfl_profile.py) — construction, `from_file` / `from_bytes`, warn-and-persist `save` (clean and with-violations paths).
- [tests/test_real_profiles.py](tests/test_real_profiles.py) — pinned violation counts against `TST-OFF1.prf` / `TST-DEF1.prf`; regressions surface here.

`tests/conftest.py::make_compliant_profile` builds a profile that satisfies every rule — tests mutate only the situation under inspection.
