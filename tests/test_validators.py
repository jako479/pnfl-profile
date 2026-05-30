"""Per-rule validator tests.

Each test starts from a PNFL-compliant baseline (`offense_profile` /
`defense_profile` fixtures), mutates one situation or one profile-wide field,
and asserts which rule fires (or doesn't).
"""

from __future__ import annotations

from dataclasses import replace

import pytest
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
    DEFENSE_CATEGORIES,
    FIELD_GOAL_PAT,
    GOAL_LINE_PASS,
    GOAL_LINE_RUN,
    OFFENSE_CATEGORIES,
    PASS_LONG_LEFT,
    PASS_LONG_RIGHT,
    PASS_MEDIUM_LEFT,
    PASS_MEDIUM_MIDDLE,
    PASS_MEDIUM_RIGHT,
    PASS_SHORT_LEFT,
    PASS_SHORT_MIDDLE,
    PASS_SHORT_RIGHT,
    PUNT,
    RAZZLE_DAZZLE_PASS,
    RUN_CLOCK,
    RUN_LEFT,
    RUN_MIDDLE,
    RUN_RIGHT,
    SituationRule,
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


def test_under_5_min_inside_own_5_still_enforces_2_categories_offense(offense_profile: Profile) -> None:
    """Inside the offense's own 5, the relaxed 2-category minimum applies even when <= 5:00."""
    n = situation_number(
        Down.FIRST,
        YardsToGo.OVER_TEN,
        FieldPosition.INSIDE_OFF_5,
        minutes=MinutesRemaining.TWO_TO_FIVE,
    )
    profile = replace_situation(
        offense_profile,
        n,
        category_weights=weights(RUN_MIDDLE, 10, RUN_MIDDLE, 0, RUN_MIDDLE, 0),
    )
    rules = {v.rule_name for v in _violate(profile) if v.situation_number == n}
    assert "offense_min_categories" in rules


def test_under_5_min_inside_own_5_passes_with_2_categories_offense(offense_profile: Profile) -> None:
    """Inside own 5 with 2 distinct categories at <= 5:00: no violation."""
    n = situation_number(
        Down.FIRST,
        YardsToGo.OVER_TEN,
        FieldPosition.INSIDE_OFF_5,
        minutes=MinutesRemaining.TWO_TO_FIVE,
    )
    profile = replace_situation(
        offense_profile,
        n,
        category_weights=weights(RUN_MIDDLE, 5, PASS_SHORT_LEFT, 5, RAZZLE_DAZZLE_PASS, 0),
    )
    rules = {v.rule_name for v in _violate(profile) if v.situation_number == n}
    assert rules == set()


def test_under_5_min_inside_own_5_still_enforces_2_categories_defense(defense_profile: Profile) -> None:
    """Inside the defense's own 5 (INSIDE_DEF_5), the relaxed 2-category minimum applies even when <= 5:00."""
    n = situation_number(
        Down.FIRST,
        YardsToGo.ZERO_TO_ONE,
        FieldPosition.INSIDE_DEF_5,
        minutes=MinutesRemaining.TWO_TO_FIVE,
    )
    profile = replace_situation(
        defense_profile,
        n,
        category_weights=weights(RUN_MIDDLE, 10, RUN_MIDDLE, 0, RUN_MIDDLE, 0),
    )
    rules = {v.rule_name for v in _violate(profile) if v.situation_number == n}
    assert "defense_min_categories" in rules


def test_4th_down_with_punt_category_is_waived(offense_profile: Profile) -> None:
    """4th down with a PUNT category (weight > 0) waives the min-categories check."""
    n = situation_number(Down.Fourth, YardsToGo.OVER_TEN, FieldPosition.DEF_35_TO_OFF_35)
    profile = replace_situation(
        offense_profile,
        n,
        category_weights=weights(PUNT, 10, RAZZLE_DAZZLE_PASS, 0, RAZZLE_DAZZLE_PASS, 0),
    )
    rules = {v.rule_name for v in _violate(profile) if v.situation_number == n}
    assert rules == set()


def test_4th_down_with_field_goal_category_is_waived(offense_profile: Profile) -> None:
    """4th down with a FIELD_GOAL_PAT category (weight > 0) waives the min-categories check."""
    n = situation_number(Down.Fourth, YardsToGo.OVER_TEN, FieldPosition.OFF_35_TO_OFF_5)
    profile = replace_situation(
        offense_profile,
        n,
        category_weights=weights(FIELD_GOAL_PAT, 10, RAZZLE_DAZZLE_PASS, 0, RAZZLE_DAZZLE_PASS, 0),
    )
    rules = {v.rule_name for v in _violate(profile) if v.situation_number == n}
    assert rules == set()


def test_4th_down_without_kick_enforces_min_categories(offense_profile: Profile) -> None:
    """4th down with no PUNT/FIELD_GOAL_PAT still requires the standard 3 categories."""
    n = situation_number(Down.Fourth, YardsToGo.OVER_TEN, FieldPosition.DEF_35_TO_OFF_35)
    profile = replace_situation(
        offense_profile,
        n,
        category_weights=weights(RAZZLE_DAZZLE_PASS, 10, RAZZLE_DAZZLE_PASS, 0, RAZZLE_DAZZLE_PASS, 0),
    )
    rules = {v.rule_name for v in _violate(profile) if v.situation_number == n}
    assert "offense_min_categories" in rules


def test_4th_down_under_5min_with_punt_is_waived(offense_profile: Profile) -> None:
    """4th down + <=5:00 + PUNT (weight > 0): no violation. Kick exemption is universal."""
    n = situation_number(
        Down.Fourth,
        YardsToGo.OVER_TEN,
        FieldPosition.DEF_35_TO_OFF_35,
        minutes=MinutesRemaining.TWO_TO_FIVE,
    )
    profile = replace_situation(
        offense_profile,
        n,
        category_weights=weights(PUNT, 10, RAZZLE_DAZZLE_PASS, 0, RAZZLE_DAZZLE_PASS, 0),
    )
    rules = {v.rule_name for v in _violate(profile) if v.situation_number == n}
    assert rules == set()


def test_4th_down_under_5min_without_kick_fires_min_categories(offense_profile: Profile) -> None:
    """4th down + <=5:00 + no kick category: 2-cat min still applies."""
    n = situation_number(
        Down.Fourth,
        YardsToGo.OVER_TEN,
        FieldPosition.DEF_35_TO_OFF_35,
        minutes=MinutesRemaining.TWO_TO_FIVE,
    )
    profile = replace_situation(
        offense_profile,
        n,
        category_weights=weights(RAZZLE_DAZZLE_PASS, 10, RAZZLE_DAZZLE_PASS, 0, RAZZLE_DAZZLE_PASS, 0),
    )
    rules = {v.rule_name for v in _violate(profile) if v.situation_number == n}
    assert "offense_min_categories" in rules


def test_under_5min_anywhere_requires_2_categories(offense_profile: Profile) -> None:
    """<=5:00 enforces the 2-category minimum at any field position, any down (not just own 5)."""
    n = situation_number(
        Down.FIRST,
        YardsToGo.SIX_TO_TEN,
        FieldPosition.DEF_35_TO_OFF_35,  # midfield, not relaxed
        minutes=MinutesRemaining.TWO_TO_FIVE,
    )
    profile = replace_situation(
        offense_profile,
        n,
        category_weights=weights(RUN_MIDDLE, 10, RUN_MIDDLE, 0, RUN_MIDDLE, 0),
    )
    rules = {v.rule_name for v in _violate(profile) if v.situation_number == n}
    assert "offense_min_categories" in rules


def test_under_5min_anywhere_passes_with_2_categories(offense_profile: Profile) -> None:
    """<=5:00 + 2 distinct categories anywhere on the field: no violation."""
    n = situation_number(
        Down.FIRST,
        YardsToGo.SIX_TO_TEN,
        FieldPosition.DEF_35_TO_OFF_35,  # midfield, not relaxed
        minutes=MinutesRemaining.TWO_TO_FIVE,
    )
    profile = replace_situation(
        offense_profile,
        n,
        category_weights=weights(RUN_MIDDLE, 5, PASS_SHORT_LEFT, 5, RAZZLE_DAZZLE_PASS, 0),
    )
    rules = {v.rule_name for v in _violate(profile) if v.situation_number == n}
    assert rules == set()


# ---------------------------------------------------------------------------
# Exempt-category waiver — offense: {FG, PUNT, RUN_CLOCK}
# ---------------------------------------------------------------------------
#
# Waiver: if every category with weight > 0 is exempt, the min-categories rule
# is skipped (any down, any time). Matrix rules still fire. Add a non-exempt
# category and the rule applies — exempt categories count toward its total.


def _no_matrix_key(down: Down = Down.Fourth) -> int:
    """Situation key with no offense matrix rule (4th down — PNFL_RULES has none),
    so only min-categories can fire and the waiver is testable in isolation.
    """
    return situation_number(down, YardsToGo.OVER_TEN, FieldPosition.DEF_35_TO_OFF_35)


def test_offense_run_clock_only_waived(offense_profile: Profile) -> None:
    """RUN_CLOCK alone (weight > 0) is exempt — newly added to the waiver set."""
    n = _no_matrix_key()
    profile = replace_situation(
        offense_profile,
        n,
        category_weights=weights(RUN_CLOCK, 10, RAZZLE_DAZZLE_PASS, 0, RAZZLE_DAZZLE_PASS, 0),
    )
    rules = {v.rule_name for v in _violate(profile) if v.situation_number == n}
    assert rules == set()


def test_offense_punt_plus_field_goal_waived(offense_profile: Profile) -> None:
    """FG + PUNT (both exempt, 2 distinct, nothing else): waived."""
    n = _no_matrix_key()
    profile = replace_situation(
        offense_profile,
        n,
        category_weights=weights(PUNT, 5, FIELD_GOAL_PAT, 5, RAZZLE_DAZZLE_PASS, 0),
    )
    rules = {v.rule_name for v in _violate(profile) if v.situation_number == n}
    assert rules == set()


def test_offense_punt_plus_run_clock_waived(offense_profile: Profile) -> None:
    """PUNT + RUN_CLOCK (both exempt): waived."""
    n = _no_matrix_key()
    profile = replace_situation(
        offense_profile,
        n,
        category_weights=weights(PUNT, 5, RUN_CLOCK, 5, RAZZLE_DAZZLE_PASS, 0),
    )
    rules = {v.rule_name for v in _violate(profile) if v.situation_number == n}
    assert rules == set()


def test_offense_field_goal_plus_run_clock_waived(offense_profile: Profile) -> None:
    """FG + RUN_CLOCK (both exempt): waived."""
    n = _no_matrix_key()
    profile = replace_situation(
        offense_profile,
        n,
        category_weights=weights(FIELD_GOAL_PAT, 5, RUN_CLOCK, 5, RAZZLE_DAZZLE_PASS, 0),
    )
    rules = {v.rule_name for v in _violate(profile) if v.situation_number == n}
    assert rules == set()


def test_offense_all_three_exempt_waived(offense_profile: Profile) -> None:
    """FG + PUNT + RUN_CLOCK (3 distinct, all exempt): waived even though count alone would satisfy."""
    n = _no_matrix_key()
    profile = replace_situation(
        offense_profile,
        n,
        category_weights=weights(FIELD_GOAL_PAT, 4, PUNT, 3, RUN_CLOCK, 3),
    )
    rules = {v.rule_name for v in _violate(profile) if v.situation_number == n}
    assert rules == set()


def test_offense_exempt_plus_non_exempt_requires_3_distinct(offense_profile: Profile) -> None:
    """As soon as a non-exempt category appears, the 3-category rule applies.

    PUNT + RAZZLE_DAZZLE_PASS is 2 distinct categories — passes neither the
    standard 3-min nor (since this is midfield) the relaxed 2-min on its face,
    so the min-categories rule fires.
    """
    n = _no_matrix_key()
    profile = replace_situation(
        offense_profile,
        n,
        category_weights=weights(PUNT, 5, RAZZLE_DAZZLE_PASS, 5, RAZZLE_DAZZLE_PASS, 0),
    )
    rules = {v.rule_name for v in _violate(profile) if v.situation_number == n}
    assert "offense_min_categories" in rules


def test_offense_exempt_pair_plus_non_exempt_passes(offense_profile: Profile) -> None:
    """FG + PUNT + RAZZLE_DAZZLE_PASS = 3 distinct, including 2 exempt: passes the 3-min rule.

    Confirms exempt categories DO count toward the distinct-category total when
    the waiver itself doesn't apply.
    """
    n = _no_matrix_key()
    profile = replace_situation(
        offense_profile,
        n,
        category_weights=weights(FIELD_GOAL_PAT, 4, PUNT, 3, RAZZLE_DAZZLE_PASS, 3),
    )
    rules = {v.rule_name for v in _violate(profile) if v.situation_number == n}
    assert rules == set()


def test_offense_run_clock_only_under_5min_waived(offense_profile: Profile) -> None:
    """RUN_CLOCK alone under <=5:00: still waived (exemption applies any time)."""
    n = situation_number(
        Down.FIRST,
        YardsToGo.SIX_TO_TEN,
        FieldPosition.DEF_35_TO_OFF_35,
        minutes=MinutesRemaining.TWO_TO_FIVE,
    )
    profile = replace_situation(
        offense_profile,
        n,
        category_weights=weights(RUN_CLOCK, 10, RAZZLE_DAZZLE_PASS, 0, RAZZLE_DAZZLE_PASS, 0),
    )
    rules = {v.rule_name for v in _violate(profile) if v.situation_number == n}
    assert rules == set()


def test_offense_zero_weights_does_not_waive(offense_profile: Profile) -> None:
    """A situation with every weight = 0 has no categories — the waiver does NOT trigger.

    Confirms the empty-set edge case: the waiver requires at least one non-zero
    category, all of which must be exempt. Empty input still fires the min-cat rule.
    """
    n = _no_matrix_key()
    profile = replace_situation(
        offense_profile,
        n,
        category_weights=weights(RAZZLE_DAZZLE_PASS, 0, RAZZLE_DAZZLE_PASS, 0, RAZZLE_DAZZLE_PASS, 0),
    )
    rules = {v.rule_name for v in _violate(profile) if v.situation_number == n}
    assert "offense_min_categories" in rules


def test_offense_exempt_only_still_subject_to_matrix_rule(offense_profile: Profile) -> None:
    """Exemption waives min-categories, but the allowed-categories matrix still applies.

    1st-and-5 between the 5s allows only {RL, RM, PSL, PML}. Setting PUNT alone
    here waives the min-categories check (PUNT is exempt) but the allowed-cats
    rule fires because PUNT is not in the allowed set for this matrix cell.
    """
    n = situation_number(Down.FIRST, YardsToGo.TWO_TO_FIVE, FieldPosition.DEF_35_TO_OFF_35)
    profile = replace_situation(
        offense_profile,
        n,
        category_weights=weights(PUNT, 10, RAZZLE_DAZZLE_PASS, 0, RAZZLE_DAZZLE_PASS, 0),
    )
    rules = {v.rule_name for v in _violate(profile) if v.situation_number == n}
    assert "offense_allowed_categories" in rules
    assert "offense_min_categories" not in rules


# ---------------------------------------------------------------------------
# Exempt-category waiver — defense: FG / PUNT only (no RUN_CLOCK)
# ---------------------------------------------------------------------------


def _def_no_matrix_key(down: Down = Down.FIRST) -> int:
    """Defense situation key with no matrix rule (defense matrix is 3rd-down only)."""
    return situation_number(down, YardsToGo.SIX_TO_TEN, FieldPosition.DEF_35_TO_OFF_35)


def test_defense_punt_only_waived(defense_profile: Profile) -> None:
    """Defense with PUNT alone: waived (PUNT is in the defense exempt set)."""
    n = _def_no_matrix_key()
    profile = replace_situation(
        defense_profile,
        n,
        category_weights=weights(PUNT, 10, RUN_MIDDLE, 0, RUN_MIDDLE, 0),
    )
    rules = {v.rule_name for v in _violate(profile) if v.situation_number == n}
    assert rules == set()


def test_defense_field_goal_only_waived(defense_profile: Profile) -> None:
    """Defense with FIELD_GOAL_PAT alone: waived."""
    n = _def_no_matrix_key()
    profile = replace_situation(
        defense_profile,
        n,
        category_weights=weights(FIELD_GOAL_PAT, 10, RUN_MIDDLE, 0, RUN_MIDDLE, 0),
    )
    rules = {v.rule_name for v in _violate(profile) if v.situation_number == n}
    assert rules == set()


def test_defense_punt_plus_field_goal_waived(defense_profile: Profile) -> None:
    """Defense with PUNT + FG (both exempt, 2 distinct): waived."""
    n = _def_no_matrix_key()
    profile = replace_situation(
        defense_profile,
        n,
        category_weights=weights(PUNT, 5, FIELD_GOAL_PAT, 5, RUN_MIDDLE, 0),
    )
    rules = {v.rule_name for v in _violate(profile) if v.situation_number == n}
    assert rules == set()


def test_defense_run_clock_is_not_exempt(defense_profile: Profile) -> None:
    """RUN_CLOCK is NOT in the defense exempt set — defense has no Run Clock category.

    Setting RUN_CLOCK alone on defense triggers the min-categories rule because
    the situation has 1 non-exempt category (RUN_CLOCK at 0x16, not in {FG, PUNT}).
    """
    n = _def_no_matrix_key()
    profile = replace_situation(
        defense_profile,
        n,
        category_weights=weights(RUN_CLOCK, 10, RUN_MIDDLE, 0, RUN_MIDDLE, 0),
    )
    rules = {v.rule_name for v in _violate(profile) if v.situation_number == n}
    assert "defense_min_categories" in rules


def test_defense_punt_under_5min_waived(defense_profile: Profile) -> None:
    """Defense PUNT alone under <=5:00: still waived (exemption is always-on)."""
    n = situation_number(
        Down.FIRST,
        YardsToGo.SIX_TO_TEN,
        FieldPosition.DEF_35_TO_OFF_35,
        minutes=MinutesRemaining.TWO_TO_FIVE,
    )
    profile = replace_situation(
        defense_profile,
        n,
        category_weights=weights(PUNT, 10, RUN_MIDDLE, 0, RUN_MIDDLE, 0),
    )
    rules = {v.rule_name for v in _violate(profile) if v.situation_number == n}
    assert rules == set()


def test_defense_under_5min_requires_2_distinct(defense_profile: Profile) -> None:
    """Defense <=5:00: confirms 2 *distinct* categories required, not 2 plays.

    Two RUN_MIDDLE entries are one distinct category — fires min-categories.
    """
    n = situation_number(
        Down.FIRST,
        YardsToGo.SIX_TO_TEN,
        FieldPosition.DEF_35_TO_OFF_35,
        minutes=MinutesRemaining.TWO_TO_FIVE,
    )
    profile = replace_situation(
        defense_profile,
        n,
        category_weights=weights(RUN_MIDDLE, 5, RUN_MIDDLE, 5, RUN_MIDDLE, 0),
    )
    rules = {v.rule_name for v in _violate(profile) if v.situation_number == n}
    assert "defense_min_categories" in rules


def test_defense_under_5min_punt_plus_non_exempt_requires_2_distinct(defense_profile: Profile) -> None:
    """Defense <=5:00 + 1 exempt + 1 non-exempt = 2 distinct: passes (waiver doesn't apply)."""
    n = situation_number(
        Down.FIRST,
        YardsToGo.SIX_TO_TEN,
        FieldPosition.DEF_35_TO_OFF_35,
        minutes=MinutesRemaining.TWO_TO_FIVE,
    )
    profile = replace_situation(
        defense_profile,
        n,
        category_weights=weights(PUNT, 5, RUN_MIDDLE, 5, RUN_MIDDLE, 0),
    )
    rules = {v.rule_name for v in _violate(profile) if v.situation_number == n}
    assert rules == set()


def test_defense_under_5min_punt_plus_same_non_exempt_twice_fails(defense_profile: Profile) -> None:
    """<=5:00 + PUNT + RUN_MIDDLE + RUN_MIDDLE = 2 distinct (PUNT, RM): passes.

    Sanity check that PUNT counts as 1 of the 2 distinct under the relaxed minimum
    when paired with a non-exempt category.
    """
    n = situation_number(
        Down.FIRST,
        YardsToGo.SIX_TO_TEN,
        FieldPosition.DEF_35_TO_OFF_35,
        minutes=MinutesRemaining.TWO_TO_FIVE,
    )
    profile = replace_situation(
        defense_profile,
        n,
        category_weights=weights(PUNT, 3, RUN_MIDDLE, 4, RUN_MIDDLE, 3),
    )
    rules = {v.rule_name for v in _violate(profile) if v.situation_number == n}
    assert rules == set()


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


# ---------------------------------------------------------------------------
# Loop test: every matrix key has a satisfiable rule
# ---------------------------------------------------------------------------


def _compliant_weights_for(rule: SituationRule, universe: frozenset[int]) -> tuple[int, int, int]:
    """Pick 3 distinct categories that satisfy `rule`: one from each mandatory
    alternative, then fill from allowed_categories (or `universe` if unrestricted)."""
    allowed = rule.allowed_categories if rule.allowed_categories is not None else universe
    cats: list[int] = []
    for alt in rule.mandatory_alternatives:
        for c in sorted(alt):
            if c in allowed and c not in cats:
                cats.append(c)
                break
    for c in sorted(allowed):
        if len(cats) >= 3:
            break
        if c not in cats:
            cats.append(c)
    return cats[0], cats[1], cats[2]


@pytest.mark.parametrize("key", list(PNFL_RULES.offense_situations.keys()))
def test_every_offense_matrix_key_has_satisfiable_rule(offense_profile: Profile, key) -> None:
    rule = PNFL_RULES.offense_situations[key]
    c1, c2, c3 = _compliant_weights_for(rule, OFFENSE_CATEGORIES)
    n = situation_number(*key)
    profile = replace_situation(
        offense_profile,
        n,
        category_weights=weights(c1, 4, c2, 3, c3, 3),
    )
    violations = [v for v in _violate(profile) if v.situation_number == n]
    assert violations == []


@pytest.mark.parametrize("key", list(PNFL_RULES.defense_situations.keys()))
def test_every_defense_matrix_key_has_satisfiable_rule(defense_profile: Profile, key) -> None:
    rule = PNFL_RULES.defense_situations[key]
    c1, c2, c3 = _compliant_weights_for(rule, DEFENSE_CATEGORIES)
    n = situation_number(*key)
    profile = replace_situation(
        defense_profile,
        n,
        category_weights=weights(c1, 4, c2, 3, c3, 3),
    )
    violations = [v for v in _violate(profile) if v.situation_number == n]
    assert violations == []
