# pnfl-profile

PNFL league rules layered on [fbpro98-profile](../fbpro98-profile/). Wraps a `Profile` so `validate()` reports rule violations and `save()` writes regardless, emitting one `PnflRuleWarning` per violation. Composition + property forwarders (not inheritance) — see [ARCHITECTURE.md](ARCHITECTURE.md). Rules in [RULES.md](RULES.md).

## Setup

```bash
py -3.13 -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

## Usage

```python
from pnfl_profile import PnflProfile, PNFL_RULES

pp = PnflProfile.from_file("DEN-OFF1.prf", PNFL_RULES)
for v in pp.validate():
    print(f"[{v.rule_name}] sit {v.situation_number}: {v.message}")

violations = pp.save("DEN-OFF1.prf")   # writes regardless; emits PnflRuleWarning per violation
```

`pp.is_offense`, `pp.situations`, `pp.field_goal_range`, etc. are forwarded from `pp.profile`.

## Testing

```bash
pytest
```
