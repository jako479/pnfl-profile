# pnfl-profile — Architecture

Library that owns the PNFL league's coaching-profile rule set and pairs it with a `Profile` from `fbpro98-profile` for validation and rule-aware I/O.

## Module layout

```
src/pnfl_profile/
├── __init__.py    # public API re-exports
├── model.py       # PnflProfile, Violation, PnflRuleError
├── rules.py       # SituationRule, PnflRules, PNFL_RULES; play-category constants
└── validators.py  # validate_profile and per-rule helpers
```

## Composition, not inheritance

`PnflProfile` wraps a `Profile` plus a `PnflRules` instance — it does not inherit from `Profile`. Subclassing would have let `PnflProfile.save()` reject profiles that `Profile.save()` would have written, which violates Liskov substitution: code written against the `Profile` contract would silently see new exception types from a `PnflProfile` instance handed to it.

Two layers, different jobs:

- `fbpro98-profile` — file I/O for the `.prf` format. No league knowledge.
- `pnfl-profile` — PNFL semantics over a loaded `Profile`. Uses the format library for read/write.

## Rule data

`PNFL_RULES` is a frozen `PnflRules` instance defined in [rules.py](src/pnfl_profile/rules.py). The rule data is decoupled from the validator logic — alternate rule sets (a future season, a custom variant for testing) can be constructed by composing the same types, and `PnflProfile` is bound to a specific rule set at construction time.

The per-situation rules are keyed on `(Down, YardsToGo, FieldPosition)` — point spread isn't a rule input, and time is gated separately (`MinutesRemaining == OVER_FIVE`). Field position is encoded from the offense's perspective in the `.prf` format, so the "own 5-yard line" exception resolves to `INSIDE_OFF_5` on offense and `INSIDE_DEF_5` on defense.

## Validation contract

`validate_profile(profile, rules)` runs every PNFL validator and returns one `Violation` per breach. `PnflProfile.save(path)` calls it first and raises `PnflRuleError` carrying every violation if anything failed; otherwise it delegates to `fbpro98-profile`'s `write_profile`.

Validators are pure functions of the profile + rules. They never mutate.

## What this package does

- Wraps an fbpro98 `Profile` in a `PnflProfile` bound to a `PnflRules`.
- Validates every PNFL coaching-profile rule scraped from the league rules thread.
- Save-time gate: refuses to write a profile that violates any rule.

## What this package does NOT do

- File format parsing or writing — fbpro98-profile owns that.
- PAT logic, field-goal range, stop-clock, or sub-percentage rules — not specified in the rule source, so no validators yet.
- 4th-down play-category enforcement — the rule source only covers 1st-3rd downs.
- Game-plan validation — separate concern, separate package.

## Testing

- [tests/test_validators.py](tests/test_validators.py) — each rule exercised against a PNFL-compliant baseline mutated to fire that one rule.
- [tests/test_pnfl_profile.py](tests/test_pnfl_profile.py) — `PnflProfile` construction, `from_file` / `from_bytes`, `save` semantics including the no-overwrite guarantee when validation fails.
- [tests/test_real_profiles.py](tests/test_real_profiles.py) — baseline counts against real PNFL profiles (`TST-OFF1.prf`, `TST-DEF1.prf`); pinned so validator regressions surface here.

The compliant-baseline builder (`tests/conftest.py::make_compliant_profile`) constructs a profile that satisfies every rule, so individual tests only need to mutate the situation under inspection without tripping unrelated rules.
