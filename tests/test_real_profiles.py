"""Smoke baselines against real PNFL coaching profiles.

`TST-OFF1.prf` and `TST-DEF1.prf` are copies of profiles Brian actually plays
with in the PNFL league. They mostly pass the rule set but trip a known set of
violations — some from the game-editor copy bug, some from rule corners not yet
clarified. The baselines pin the current counts so a future change to the
validator (or the rule data) shows up here and prompts an explicit review.
"""

from __future__ import annotations

import collections
from pathlib import Path

import pytest

from pnfl_profile import PNFL_RULES, PnflProfile

DATA_DIR = Path(__file__).parent / "data"

OFF1_EXPECTED_VIOLATIONS = {
    "offense_allowed_categories": 5,
    "offense_mandatory_category": 11,
    "offense_min_categories": 1,
}

DEF1_EXPECTED_VIOLATIONS = {
    "defense_min_categories": 7,
}


def test_real_off1_loads() -> None:
    pp = PnflProfile.from_file(str(DATA_DIR / "TST-OFF1.prf"), PNFL_RULES)
    assert pp.profile.is_offense


def test_real_def1_loads() -> None:
    pp = PnflProfile.from_file(str(DATA_DIR / "TST-DEF1.prf"), PNFL_RULES)
    assert pp.profile.is_defense


@pytest.mark.parametrize(
    ("fixture", "expected"),
    [
        ("TST-OFF1.prf", OFF1_EXPECTED_VIOLATIONS),
        ("TST-DEF1.prf", DEF1_EXPECTED_VIOLATIONS),
    ],
)
def test_real_profile_violation_baseline(fixture: str, expected: dict[str, int]) -> None:
    """Pins the violation counts so changes in the validator or rule data are caught.

    If this fails after a deliberate rule change, update the baseline; if it
    fails unexpectedly, the validator regressed.
    """
    pp = PnflProfile.from_file(str(DATA_DIR / fixture), PNFL_RULES)
    counts = collections.Counter(v.rule_name for v in pp.validate())
    assert dict(counts) == expected
