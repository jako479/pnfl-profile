"""Per-rule validator tests.

Each test starts from a PNFL-compliant baseline (`offense_profile` /
`defense_profile` fixtures), mutates one situation or one profile-wide field,
and asserts which rule fires (or doesn't).
"""

from __future__ import annotations

from dataclasses import replace

from conftest import replace_situation, situation_number, weights
from fbpro98_profile import (
    Down,
    FieldPosition,
    MinutesRemaining,
    PointSpread,
    Profile,
    SubstitutionPair,
    YardsToGo,
)

from pnfl_profile import (
    PASS_LONG_ANY,
    PASS_MEDIUM_ANY,
    PASS_SHORT_ANY,
    PNFL_RULES,
    PnflProfile,
)
from pnfl_profile.rules import (
    GOAL_LINE_PASS,
    GOAL_LINE_RUN,
    PASS_LONG_LEFT,
    PASS_LONG_RIGHT,
    PASS_MEDIUM_LEFT,
    PASS_MEDIUM_MIDDLE,
    PASS_MEDIUM_RIGHT,
    PASS_SHORT_LEFT,
    PASS_SHORT_MIDDLE,
    PASS_SHORT_RIGHT,
    RAZZLE_DAZZLE_PASS,
    RUN_LEFT,
    RUN_MIDDLE,
    RUN_RIGHT,
)


def _violate(profile: Profile) -> tuple:
    return PnflProfile(profile=profile, rules=PNFL_RULES).validate()


def _rules_of(profile: Profile) -> set[str]:
    return {v.rule_name for v in _violate(profile)}


# ---------------------------------------------------------------------------
# Universal rules
# ---------------------------------------------------------------------------


def test_audibles_unchecked_passes(offense_profile: Profile) -> None:
    assert "audibles_unchecked" not in _rules_of(offense_profile)


def test_audibles_checked_violates(offense_profile: Profile) -> None:
    profile = replace(offense_profile, use_audibles=True)
    rules = _rules_of(profile)
    assert "audibles_unchecked" in rules


def test_audibles_checked_on_defense_also_violates(defense_profile: Profile) -> None:
    profile = replace(defense_profile, use_audibles=True)
    assert "audibles_unchecked" in _rules_of(profile)


# ---------------------------------------------------------------------------
# QB substitution
# ---------------------------------------------------------------------------


def test_offense_qb_substitution_75_80_passes(offense_profile: Profile) -> None:
    assert "offense_qb_substitution" not in _rules_of(offense_profile)


def test_offense_qb_substitution_wrong_violates(offense_profile: Profile) -> None:
    subs = replace(offense_profile.substitutions, quarterbacks=SubstitutionPair(80, 90))
    profile = replace(offense_profile, substitutions=subs)
    assert "offense_qb_substitution" in _rules_of(profile)


def test_defense_qb_substitution_not_checked(defense_profile: Profile) -> None:
    # Defense QB sub may be anything (rule is offense-only).
    subs = replace(defense_profile.substitutions, quarterbacks=SubstitutionPair(80, 90))
    profile = replace(defense_profile, substitutions=subs)
    assert "offense_qb_substitution" not in _rules_of(profile)


# ---------------------------------------------------------------------------
# Min-categories (offense and defense, standard + relaxed)
# ---------------------------------------------------------------------------


def test_offense_min_categories_2_violates_standard_3(offense_profile: Profile) -> None:
    n = situation_number(Down.FIRST, YardsToGo.SIX_TO_TEN, FieldPosition.DEF_35_TO_OFF_35)
    profile = replace_situation(
        offense_profile,
        n,
        category_weights=weights(RUN_MIDDLE, 5, PASS_SHORT_LEFT, 5, PASS_MEDIUM_LEFT, 0),
    )
    violations = _violate(profile)
    fired = [v for v in violations if v.situation_number == n]
    assert any(v.rule_name == "offense_min_categories" for v in fired)


def test_offense_min_categories_2_passes_inside_own_5(offense_profile: Profile) -> None:
    n = situation_number(Down.FIRST, YardsToGo.OVER_TEN, FieldPosition.INSIDE_OFF_5)
    profile = replace_situation(
        offense_profile,
        n,
        category_weights=weights(RUN_MIDDLE, 5, PASS_SHORT_LEFT, 5, PASS_MEDIUM_LEFT, 0),
    )
    rules = {v.rule_name for v in _violate(profile) if v.situation_number == n}
    assert "offense_min_categories" not in rules


def test_offense_min_categories_1_fails_even_inside_own_5(offense_profile: Profile) -> None:
    n = situation_number(Down.FIRST, YardsToGo.OVER_TEN, FieldPosition.INSIDE_OFF_5)
    profile = replace_situation(
        offense_profile,
        n,
        category_weights=weights(RUN_MIDDLE, 10, PASS_SHORT_LEFT, 0, PASS_MEDIUM_LEFT, 0),
    )
    rules = {v.rule_name for v in _violate(profile) if v.situation_number == n}
    assert "offense_min_categories" in rules


def test_defense_min_categories_2_violates_standard_3(defense_profile: Profile) -> None:
    n = situation_number(Down.FIRST, YardsToGo.SIX_TO_TEN, FieldPosition.DEF_35_TO_OFF_35)
    profile = replace_situation(
        defense_profile,
        n,
        category_weights=weights(RUN_MIDDLE, 5, PASS_SHORT_MIDDLE, 5, PASS_MEDIUM_MIDDLE, 0),
    )
    assert any(v.rule_name == "defense_min_categories" and v.situation_number == n for v in _violate(profile))


def test_defense_relaxed_min_inside_def_5(defense_profile: Profile) -> None:
    """Defense at own 5 (= offense in red zone = INSIDE_DEF_5) drops the min to 2."""
    n = situation_number(Down.FIRST, YardsToGo.ZERO_TO_ONE, FieldPosition.INSIDE_DEF_5)
    profile = replace_situation(
        defense_profile,
        n,
        category_weights=weights(RUN_MIDDLE, 5, PASS_SHORT_MIDDLE, 5, PASS_MEDIUM_MIDDLE, 0),
    )
    rules = {v.rule_name for v in _violate(profile) if v.situation_number == n}
    assert "defense_min_categories" not in rules


# ---------------------------------------------------------------------------
# Time / down gating
# ---------------------------------------------------------------------------


def test_under_5_min_rules_are_waived(offense_profile: Profile) -> None:
    """1st-6-10 between-5s allows {RM, PSL, PML}; passing PLR violates if >5 min..."""
    n_under5 = situation_number(
        Down.FIRST,
        YardsToGo.SIX_TO_TEN,
        FieldPosition.DEF_35_TO_OFF_35,
        minutes=MinutesRemaining.TWO_TO_FIVE,
    )
    profile = replace_situation(
        offense_profile,
        n_under5,
        category_weights=weights(PASS_LONG_RIGHT, 4, PASS_LONG_LEFT, 3, RAZZLE_DAZZLE_PASS, 3),
    )
    rules = {v.rule_name for v in _violate(profile) if v.situation_number == n_under5}
    # ...but inside 5 min it's free: no allowed/mandatory violations.
    assert "offense_allowed_categories" not in rules
    assert "offense_min_categories" not in rules


def test_4th_down_is_not_rule_enforced(offense_profile: Profile) -> None:
    n = situation_number(Down.Fourth, YardsToGo.OVER_TEN, FieldPosition.DEF_35_TO_OFF_35)
    profile = replace_situation(
        offense_profile,
        n,
        category_weights=weights(RAZZLE_DAZZLE_PASS, 10, RAZZLE_DAZZLE_PASS, 0, RAZZLE_DAZZLE_PASS, 0),
    )
    rules = {v.rule_name for v in _violate(profile) if v.situation_number == n}
    assert rules == set()  # 4th down never fires PNFL category rules


# ---------------------------------------------------------------------------
# Offensive matrix — 1st down
# ---------------------------------------------------------------------------


def test_offense_1st_0_1_allowed(offense_profile: Profile) -> None:
    """1st-0-1 (any field): allowed = {RM, RL, PSL, PML, GLP, GLR}; PLR is disallowed."""
    n = situation_number(Down.FIRST, YardsToGo.ZERO_TO_ONE, FieldPosition.DEF_35_TO_OFF_35)
    profile = replace_situation(
        offense_profile,
        n,
        category_weights=weights(RUN_MIDDLE, 4, PASS_LONG_RIGHT, 3, PASS_MEDIUM_LEFT, 3),
    )
    rules = {v.rule_name for v in _violate(profile) if v.situation_number == n}
    assert "offense_allowed_categories" in rules


def test_offense_1st_6_10_between_disallows_run_left(offense_profile: Profile) -> None:
    """1st-6-10 between-5s: allowed = {RM, PSL, PML} (RL not allowed)."""
    n = situation_number(Down.FIRST, YardsToGo.SIX_TO_TEN, FieldPosition.DEF_5_TO_DEF_35)
    profile = replace_situation(
        offense_profile,
        n,
        category_weights=weights(RUN_MIDDLE, 4, RUN_LEFT, 3, PASS_SHORT_LEFT, 3),
    )
    rules = {v.rule_name for v in _violate(profile) if v.situation_number == n}
    assert "offense_allowed_categories" in rules


def test_offense_1st_over_10_unrestricted(offense_profile: Profile) -> None:
    """1st->10 has no allowed-set restriction; any categories pass."""
    n = situation_number(Down.FIRST, YardsToGo.OVER_TEN, FieldPosition.DEF_35_TO_OFF_35)
    profile = replace_situation(
        offense_profile,
        n,
        category_weights=weights(PASS_LONG_RIGHT, 4, PASS_SHORT_RIGHT, 3, PASS_MEDIUM_RIGHT, 3),
    )
    rules = {v.rule_name for v in _violate(profile) if v.situation_number == n}
    assert rules == set()


# ---------------------------------------------------------------------------
# Offensive matrix — 2nd down
# ---------------------------------------------------------------------------


def test_offense_2nd_6_10_between_disallows_run_left(offense_profile: Profile) -> None:
    """2nd-6-10 between-5s: allowed = {RM, RR, PSM, PMM} (RL not allowed)."""
    n = situation_number(Down.SECOND, YardsToGo.SIX_TO_TEN, FieldPosition.DEF_5_TO_DEF_35)
    profile = replace_situation(
        offense_profile,
        n,
        category_weights=weights(RUN_MIDDLE, 4, RUN_LEFT, 3, PASS_SHORT_MIDDLE, 3),
    )
    rules = {v.rule_name for v in _violate(profile) if v.situation_number == n}
    assert "offense_allowed_categories" in rules


def test_offense_2nd_6_10_between_allows_run_right(offense_profile: Profile) -> None:
    n = situation_number(Down.SECOND, YardsToGo.SIX_TO_TEN, FieldPosition.DEF_5_TO_DEF_35)
    profile = replace_situation(
        offense_profile,
        n,
        category_weights=weights(RUN_MIDDLE, 4, RUN_RIGHT, 3, PASS_SHORT_MIDDLE, 3),
    )
    rules = {v.rule_name for v in _violate(profile) if v.situation_number == n}
    assert rules == set()


def test_offense_2nd_6_10_inside_off5_allows_run_left(offense_profile: Profile) -> None:
    """Inside OFF 5 still has allowed/mandatory rules — relaxed only affects min."""
    n = situation_number(Down.SECOND, YardsToGo.SIX_TO_TEN, FieldPosition.INSIDE_OFF_5)
    profile = replace_situation(
        offense_profile,
        n,
        category_weights=weights(RUN_LEFT, 4, GOAL_LINE_PASS, 3, GOAL_LINE_RUN, 3),
    )
    rules = {v.rule_name for v in _violate(profile) if v.situation_number == n}
    assert rules == set()


# ---------------------------------------------------------------------------
# Offensive matrix — 3rd down (no-RDP and mandatories)
# ---------------------------------------------------------------------------


def test_offense_3rd_0_1_disallows_rdp(offense_profile: Profile) -> None:
    n = situation_number(Down.THIRD, YardsToGo.ZERO_TO_ONE, FieldPosition.DEF_35_TO_OFF_35)
    profile = replace_situation(
        offense_profile,
        n,
        category_weights=weights(RUN_MIDDLE, 4, RAZZLE_DAZZLE_PASS, 3, PASS_SHORT_RIGHT, 3),
    )
    rules = {v.rule_name for v in _violate(profile) if v.situation_number == n}
    assert "offense_allowed_categories" in rules


def test_offense_3rd_2_5_between_requires_psr(offense_profile: Profile) -> None:
    n = situation_number(Down.THIRD, YardsToGo.TWO_TO_FIVE, FieldPosition.DEF_35_TO_OFF_35)
    profile = replace_situation(
        offense_profile,
        n,
        category_weights=weights(RUN_MIDDLE, 4, PASS_SHORT_LEFT, 3, PASS_MEDIUM_LEFT, 3),
    )
    rules = {v.rule_name for v in _violate(profile) if v.situation_number == n}
    assert "offense_mandatory_category" in rules


def test_offense_3rd_2_5_inside_def5_no_mandatory(offense_profile: Profile) -> None:
    """The PSR-mandatory rule applies only between-5s; INSIDE_DEF_5 is free."""
    n = situation_number(Down.THIRD, YardsToGo.TWO_TO_FIVE, FieldPosition.INSIDE_DEF_5)
    profile = replace_situation(
        offense_profile,
        n,
        category_weights=weights(RUN_MIDDLE, 4, PASS_SHORT_LEFT, 3, PASS_MEDIUM_LEFT, 3),
    )
    rules = {v.rule_name for v in _violate(profile) if v.situation_number == n}
    assert "offense_mandatory_category" not in rules


def test_offense_3rd_6_10_between_requires_pmr(offense_profile: Profile) -> None:
    n = situation_number(Down.THIRD, YardsToGo.SIX_TO_TEN, FieldPosition.DEF_35_TO_OFF_35)
    profile = replace_situation(
        offense_profile,
        n,
        category_weights=weights(RUN_MIDDLE, 4, PASS_SHORT_LEFT, 3, PASS_MEDIUM_LEFT, 3),
    )
    rules = {v.rule_name for v in _violate(profile) if v.situation_number == n}
    assert "offense_mandatory_category" in rules


def test_offense_3rd_over_10_def35_to_off5_requires_plr(offense_profile: Profile) -> None:
    n = situation_number(Down.THIRD, YardsToGo.OVER_TEN, FieldPosition.DEF_35_TO_OFF_35)
    profile = replace_situation(
        offense_profile,
        n,
        category_weights=weights(RUN_MIDDLE, 4, PASS_SHORT_RIGHT, 3, PASS_MEDIUM_RIGHT, 3),
    )
    rules = {v.rule_name for v in _violate(profile) if v.situation_number == n}
    assert "offense_mandatory_category" in rules


def test_offense_3rd_over_10_def5_to_def35_no_mandatory(offense_profile: Profile) -> None:
    n = situation_number(Down.THIRD, YardsToGo.OVER_TEN, FieldPosition.DEF_5_TO_DEF_35)
    profile = replace_situation(
        offense_profile,
        n,
        category_weights=weights(RUN_MIDDLE, 4, PASS_SHORT_RIGHT, 3, PASS_MEDIUM_RIGHT, 3),
    )
    rules = {v.rule_name for v in _violate(profile) if v.situation_number == n}
    assert "offense_mandatory_category" not in rules


# ---------------------------------------------------------------------------
# Defensive matrix
# ---------------------------------------------------------------------------


def test_defense_3rd_2_5_between_requires_pass_short_any(defense_profile: Profile) -> None:
    n = situation_number(Down.THIRD, YardsToGo.TWO_TO_FIVE, FieldPosition.DEF_35_TO_OFF_35)
    profile = replace_situation(
        defense_profile,
        n,
        category_weights=weights(RUN_MIDDLE, 4, PASS_MEDIUM_MIDDLE, 3, PASS_LONG_LEFT, 3),
    )
    rules = {v.rule_name for v in _violate(profile) if v.situation_number == n}
    assert "defense_mandatory_category" in rules


def test_defense_3rd_2_5_between_any_pass_short_direction_satisfies(defense_profile: Profile) -> None:
    """Defense doesn't distinguish pass direction — PSL satisfies "PS mandatory"."""
    assert PASS_SHORT_LEFT in PASS_SHORT_ANY
    n = situation_number(Down.THIRD, YardsToGo.TWO_TO_FIVE, FieldPosition.DEF_35_TO_OFF_35)
    profile = replace_situation(
        defense_profile,
        n,
        category_weights=weights(RUN_MIDDLE, 4, PASS_SHORT_LEFT, 3, PASS_MEDIUM_MIDDLE, 3),
    )
    rules = {v.rule_name for v in _violate(profile) if v.situation_number == n}
    assert "defense_mandatory_category" not in rules


def test_defense_3rd_6_10_between_requires_pass_medium(defense_profile: Profile) -> None:
    assert PASS_MEDIUM_RIGHT in PASS_MEDIUM_ANY
    n = situation_number(Down.THIRD, YardsToGo.SIX_TO_TEN, FieldPosition.DEF_35_TO_OFF_35)
    profile = replace_situation(
        defense_profile,
        n,
        category_weights=weights(RUN_MIDDLE, 4, PASS_SHORT_MIDDLE, 3, PASS_LONG_LEFT, 3),
    )
    rules = {v.rule_name for v in _violate(profile) if v.situation_number == n}
    assert "defense_mandatory_category" in rules


def test_defense_3rd_over_10_def35_to_off5_requires_pass_long(defense_profile: Profile) -> None:
    assert PASS_LONG_LEFT in PASS_LONG_ANY
    n = situation_number(Down.THIRD, YardsToGo.OVER_TEN, FieldPosition.DEF_35_TO_OFF_35)
    profile = replace_situation(
        defense_profile,
        n,
        category_weights=weights(RUN_MIDDLE, 4, PASS_SHORT_MIDDLE, 3, PASS_MEDIUM_MIDDLE, 3),
    )
    rules = {v.rule_name for v in _violate(profile) if v.situation_number == n}
    assert "defense_mandatory_category" in rules


def test_defense_3rd_over_10_def5_to_def35_no_mandatory(defense_profile: Profile) -> None:
    """PL-mandatory only applies DEF_35-OFF_5; DEF_5-DEF_35 is free."""
    n = situation_number(Down.THIRD, YardsToGo.OVER_TEN, FieldPosition.DEF_5_TO_DEF_35)
    profile = replace_situation(
        defense_profile,
        n,
        category_weights=weights(RUN_MIDDLE, 4, PASS_SHORT_MIDDLE, 3, PASS_MEDIUM_MIDDLE, 3),
    )
    rules = {v.rule_name for v in _violate(profile) if v.situation_number == n}
    assert "defense_mandatory_category" not in rules


# ---------------------------------------------------------------------------
# Point spread doesn't affect rules
# ---------------------------------------------------------------------------


def test_rules_apply_uniformly_across_spreads(offense_profile: Profile) -> None:
    """A violation at TIED should also fire at AHEAD_8_OR_MORE — spread is not a rule input."""
    targets = []
    for spread in (PointSpread.TIED, PointSpread.AHEAD_8_OR_MORE):
        n = situation_number(
            Down.FIRST,
            YardsToGo.SIX_TO_TEN,
            FieldPosition.DEF_5_TO_DEF_35,
            spread=spread,
        )
        targets.append(n)

    profile = offense_profile
    for n in targets:
        profile = replace_situation(
            profile,
            n,
            category_weights=weights(RUN_LEFT, 4, PASS_SHORT_LEFT, 3, PASS_MEDIUM_LEFT, 3),
        )
    violations = _violate(profile)
    fired_at = {v.situation_number for v in violations if v.rule_name == "offense_allowed_categories"}
    assert set(targets).issubset(fired_at)
