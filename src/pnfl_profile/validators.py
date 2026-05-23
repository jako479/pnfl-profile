"""Validators that surface PNFL-rule violations in a `Profile`.

Each validator function returns a list of `Violation`. `validate_profile` is the
public entry point used by `PnflProfile.validate()`.
"""

from __future__ import annotations

from fbpro98_profile import (
    CategoryWeights,
    Down,
    MinutesRemaining,
    Profile,
    Situation,
)

from pnfl_profile.model import Violation
from pnfl_profile.rules import PnflRules, SituationRule


def validate_profile(profile: Profile, rules: PnflRules) -> tuple[Violation, ...]:
    """Run every PNFL validator against `profile` and return the combined report."""
    violations: list[Violation] = []
    violations.extend(_validate_audibles(profile, rules))
    violations.extend(_validate_substitutions(profile, rules))
    violations.extend(_validate_situations(profile, rules))
    return tuple(violations)


# ---------------------------------------------------------------------------
# Profile-wide validators
# ---------------------------------------------------------------------------


def _validate_audibles(profile: Profile, rules: PnflRules) -> list[Violation]:
    if rules.audibles_allowed or not profile.use_audibles:
        return []
    return [
        Violation(
            rule_name="audibles_unchecked",
            message="Audibles must be unchecked in all PNFL profiles.",
        )
    ]


def _validate_substitutions(profile: Profile, rules: PnflRules) -> list[Violation]:
    if not profile.is_offense or rules.offense_qb_substitution is None:
        return []
    required = rules.offense_qb_substitution
    actual = profile.substitutions.quarterbacks
    if actual == required:
        return []
    return [
        Violation(
            rule_name="offense_qb_substitution",
            message=(
                f"Offensive QB substitution must be {required.out_percent}/{required.in_percent}, "
                f"got {actual.out_percent}/{actual.in_percent}."
            ),
        )
    ]


# ---------------------------------------------------------------------------
# Per-situation validators
# ---------------------------------------------------------------------------


def _validate_situations(profile: Profile, rules: PnflRules) -> list[Violation]:
    if profile.is_offense:
        side_rules = rules.offense_situations
        relaxed_positions = rules.offense_relaxed_field_positions
        side = "offense"
    else:
        side_rules = rules.defense_situations
        relaxed_positions = rules.defense_relaxed_field_positions
        side = "defense"

    violations: list[Violation] = []
    for situation in profile.situations:
        # Rules only apply when more than 5 minutes remain in the half.
        if situation.minutes_remaining != MinutesRemaining.OVER_FIVE:
            continue

        # 4th down: punt/FG situations have no PNFL category minimum.
        if situation.down == Down.Fourth:
            continue

        relaxed = situation.field_position in relaxed_positions
        side_min = rules.min_categories_relaxed if relaxed else rules.min_categories_standard

        rule = side_rules.get((situation.down, situation.yards_to_go, situation.field_position))
        if rule is None:
            # No matrix-specific rule — only the side-wide min applies.
            violations.extend(_check_min_distinct(situation, side_min, side))
            continue

        effective_min = min(rule.min_distinct_categories, side_min)
        violations.extend(_check_situation_rule(situation, rule, effective_min, side))

    return violations


def _check_situation_rule(
    situation: Situation,
    rule: SituationRule,
    effective_min: int,
    side: str,
) -> list[Violation]:
    violations: list[Violation] = []
    cats_with_weight = _categories_with_weight(situation.category_weights)

    if rule.allowed_categories is not None:
        disallowed = sorted(cats_with_weight - rule.allowed_categories)
        if disallowed:
            violations.append(
                Violation(
                    rule_name=f"{side}_allowed_categories",
                    message=(
                        f"Situation {situation.situation_number} uses disallowed categories: "
                        f"{', '.join(f'0x{c:02X}' for c in disallowed)}"
                    ),
                    situation_number=situation.situation_number,
                )
            )

    for alternative in rule.mandatory_alternatives:
        if not (cats_with_weight & alternative):
            choices = ", ".join(f"0x{c:02X}" for c in sorted(alternative))
            violations.append(
                Violation(
                    rule_name=f"{side}_mandatory_category",
                    message=(
                        f"Situation {situation.situation_number} is missing a mandatory category (one of: {choices})"
                    ),
                    situation_number=situation.situation_number,
                )
            )

    if len(cats_with_weight) < effective_min:
        violations.append(
            Violation(
                rule_name=f"{side}_min_categories",
                message=(
                    f"Situation {situation.situation_number} has {len(cats_with_weight)} "
                    f"category(ies) with non-zero weight; PNFL requires {effective_min}."
                ),
                situation_number=situation.situation_number,
            )
        )

    return violations


def _check_min_distinct(situation: Situation, minimum: int, side: str) -> list[Violation]:
    cats = _categories_with_weight(situation.category_weights)
    if len(cats) >= minimum:
        return []
    return [
        Violation(
            rule_name=f"{side}_min_categories",
            message=(
                f"Situation {situation.situation_number} has {len(cats)} "
                f"category(ies) with non-zero weight; PNFL requires {minimum}."
            ),
            situation_number=situation.situation_number,
        )
    ]


def _categories_with_weight(weights: CategoryWeights) -> frozenset[int]:
    """Distinct play-category codes that appear with weight > 0."""
    return frozenset(
        cat
        for cat, weight in (
            (weights.play_category1, weights.weight1),
            (weights.play_category2, weights.weight2),
            (weights.play_category3, weights.weight3),
        )
        if weight > 0
    )


__all__ = ["validate_profile"]
