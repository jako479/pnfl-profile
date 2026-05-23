"""Shared fixtures and builders for pnfl-profile tests.

Each test that needs a profile starts from `make_compliant_profile()`, which
produces a PNFL-rules-compliant baseline for both offense and defense, then
mutates only the situation(s) it cares about. This keeps every test isolated
to one rule and avoids spurious min-category violations from a zero-weighted
default.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from fbpro98_profile import (
    CategoryWeights,
    Down,
    FieldPosition,
    PatSituation,
    Profile,
    ProfileType,
    Situation,
    SubstitutionPair,
    SubstitutionSettings,
    YardsToGo,
)

from pnfl_profile.rules import (
    PASS_LONG_MIDDLE,
    PASS_LONG_RIGHT,
    PASS_MEDIUM_LEFT,
    PASS_MEDIUM_MIDDLE,
    PASS_MEDIUM_RIGHT,
    PASS_SHORT_LEFT,
    PASS_SHORT_MIDDLE,
    PASS_SHORT_RIGHT,
    PUNT,
    RUN_MIDDLE,
)

DATA_DIR = Path(__file__).parent / "data"


def _compliant_offense_categories(down: Down, yards: YardsToGo, field: FieldPosition) -> tuple[int, int, int]:
    """Three play categories that satisfy every PNFL offensive rule for this cell."""
    if down == Down.FIRST:
        return (RUN_MIDDLE, PASS_SHORT_LEFT, PASS_MEDIUM_LEFT)
    if down == Down.SECOND:
        return (RUN_MIDDLE, PASS_SHORT_MIDDLE, PASS_MEDIUM_MIDDLE)
    if down == Down.THIRD:
        if yards == YardsToGo.TWO_TO_FIVE:
            # PSR mandatory between-5s; legal everywhere else too.
            return (RUN_MIDDLE, PASS_SHORT_RIGHT, PASS_MEDIUM_RIGHT)
        if yards == YardsToGo.SIX_TO_TEN:
            return (RUN_MIDDLE, PASS_MEDIUM_RIGHT, PASS_SHORT_RIGHT)
        if yards == YardsToGo.OVER_TEN:
            # PLR mandatory DEF_35-OFF_5; legal everywhere else.
            return (RUN_MIDDLE, PASS_LONG_RIGHT, PASS_SHORT_RIGHT)
        return (RUN_MIDDLE, PASS_SHORT_RIGHT, PASS_MEDIUM_RIGHT)
    # 4th down: not rule-enforced; pick a generic punt-ish set.
    _ = field
    return (PUNT, RUN_MIDDLE, PASS_SHORT_MIDDLE)


def _compliant_defense_categories(down: Down, yards: YardsToGo, field: FieldPosition) -> tuple[int, int, int]:
    """Three play categories that satisfy every PNFL defensive rule for this cell."""
    if (
        down == Down.THIRD
        and yards == YardsToGo.OVER_TEN
        and field
        in (
            FieldPosition.DEF_35_TO_OFF_35,
            FieldPosition.OFF_35_TO_OFF_5,
        )
    ):
        return (RUN_MIDDLE, PASS_MEDIUM_MIDDLE, PASS_LONG_MIDDLE)
    return (RUN_MIDDLE, PASS_SHORT_MIDDLE, PASS_MEDIUM_MIDDLE)


def weights(c1: int, w1: int, c2: int, w2: int, c3: int, w3: int) -> CategoryWeights:
    return CategoryWeights(
        play_category1=c1,
        weight1=w1,
        play_category2=c2,
        weight2=w2,
        play_category3=c3,
        weight3=w3,
    )


def _compliant_situation(n: int, profile_type: ProfileType) -> Situation:
    _minutes, down, yards, field, _spread = Situation._game_state_from_situation_number(n)
    picker = _compliant_offense_categories if profile_type == ProfileType.OFFENSE else _compliant_defense_categories
    c1, c2, c3 = picker(down, yards, field)
    return Situation.from_situation_number(
        situation_number=n,
        stop_clock=False,
        category_weights=weights(c1, 4, c2, 3, c3, 3),
    )


def _compliant_pat_situation(n: int) -> PatSituation:
    return PatSituation.from_situation_number(
        situation_number=n,
        category_weights=weights(0x10, 10, 0x11, 0, 0x12, 0),  # FIELD_GOAL_PAT
    )


def _qb_sub_75_80() -> SubstitutionSettings:
    default = SubstitutionPair(80, 90)
    return SubstitutionSettings(
        offensive_linemen=default,
        quarterbacks=SubstitutionPair(75, 80),
        running_backs=default,
        receivers=default,
        defensive_linemen=default,
        linebackers=default,
        defensive_backs=default,
        kickers=default,
    )


def make_compliant_profile(profile_type: ProfileType = ProfileType.OFFENSE) -> Profile:
    """Build a baseline Profile that satisfies every PNFL rule.

    Tests mutate one situation (or one profile-wide field) to isolate the rule
    under test. Without this baseline, every test would also trip the min-category
    rule everywhere — the zero-weight default profile is not PNFL-compliant.
    """
    return Profile(
        profile_type=profile_type,
        substitutions=_qb_sub_75_80() if profile_type == ProfileType.OFFENSE else SubstitutionSettings.default(),
        situations=tuple(_compliant_situation(n, profile_type) for n in range(1, Profile.NUMBER_SITUATIONS + 1)),
        pat_situations=tuple(_compliant_pat_situation(n) for n in range(1, Profile.NUMBER_PAT_SITUATIONS + 1)),
        field_goal_range=35,
        use_audibles=False,
    )


def replace_situation(profile: Profile, situation_number: int, **changes) -> Profile:
    """Return `profile` with the situation at `situation_number` replaced via `dataclasses.replace`."""
    idx = situation_number - 1
    new_situation = replace(profile.situations[idx], **changes)
    new_situations = (*profile.situations[:idx], new_situation, *profile.situations[idx + 1 :])
    return replace(profile, situations=new_situations)


def situation_number(
    down: Down,
    yards: YardsToGo,
    field: FieldPosition,
    minutes=None,
    spread=None,
) -> int:
    """Look up the situation_number for a given game state."""
    from fbpro98_profile import MinutesRemaining, PointSpread

    return Situation._situation_number_from_game_state(
        minutes_remaining=minutes if minutes is not None else MinutesRemaining.OVER_FIVE,
        down=down,
        yards_to_go=yards,
        field_position=field,
        point_spread=spread if spread is not None else PointSpread.TIED,
    )


@pytest.fixture
def offense_profile() -> Profile:
    return make_compliant_profile(ProfileType.OFFENSE)


@pytest.fixture
def defense_profile() -> Profile:
    return make_compliant_profile(ProfileType.DEFENSE)
