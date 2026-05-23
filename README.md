# pnfl-profile

PNFL league rules and validation layered on top of [fbpro98-profile](../fbpro98-profile/). Wraps an fbpro98 `Profile` with the PNFL rule set so save-time validation, rule-violation reporting, and rule-aware tooling all see the same source of truth.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -e ".[dev]"
```

## Usage

```python
from pnfl_profile import PnflProfile, PNFL_RULES

# Load and validate
pp = PnflProfile.from_file("DEN-OFF1.prf", PNFL_RULES)
for v in pp.validate():
    print(f"[{v.rule_name}] sit {v.situation_number}: {v.message}")

# Save — validates first and raises PnflRuleError if anything fails
pp.save("DEN-OFF1.prf")
```

`PnflProfile` is composed of an underlying `Profile` plus a `PnflRules` instance — it does not inherit from `Profile`. See [ARCHITECTURE.md](ARCHITECTURE.md) for the reasoning.

```python
pp.profile     # underlying fbpro98_profile.Profile
pp.rules       # PnflRules currently bound to this profile
pp.validate()  # tuple[Violation, ...]
pp.save(path)  # raises PnflRuleError on violations; otherwise writes
```

## Rule data

`PNFL_RULES` is the canonical rule set, sourced from the league's [coaching-profile rules thread](https://pnfl.biz/messageboard/viewtopic.php?f=18&t=28). It captures:

- No audibles, on either side.
- Offensive QB substitution = 75/80.
- The 1st-/2nd-/3rd-down allowed-category and mandatory-category matrix for offense, keyed on (down, yards-to-go, field position).
- The 3rd-down mandatory `PASS_SHORT` / `PASS_MEDIUM` / `PASS_LONG` cells for defense.
- A 3-category minimum (relaxed to 2 when the team is within its own 5-yard line) for both sides while more than 5 minutes remain in the half.

Construct a `PnflRules` directly to model a different season or a custom variant.

## Testing

```bash
pytest
```
