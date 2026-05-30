"""Validators that surface PNFL-rule violations in a `Profile`.

Each validator function returns a list of `Violation`. `validate_profile` is the
public entry point used by `PnflProfile.validate()`.
"""

from __future__ import annotations

from dataclasses import dataclass

from fbpro98_profile import (
    CategoryWeights,
    MinutesRemaining,
    Profile,
    Situation,
)

from pnfl_profile.model import RuleName, Violation
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
            rule_name=RuleName.AUDIBLES_UNCHECKED,
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
            rule_name=RuleName.OFFENSE_QB_SUBSTITUTION,
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
        exempt = rules.offense_exempt_categories
        names = _OFFENSE_NAMES
    else:
        side_rules = rules.defense_situations
        relaxed_positions = rules.defense_relaxed_field_positions
        exempt = rules.defense_exempt_categories
        names = _DEFENSE_NAMES

    violations: list[Violation] = []
    for situation in profile.situations:
        cats_with_weight = _categories_with_weight(situation.category_weights)

        # Waive min-categories when every category with weight > 0 is exempt.
        # Matrix rules below still fire.
        waive_min_categories = bool(cats_with_weight) and cats_with_weight.issubset(exempt)

        if situation.minutes_remaining != MinutesRemaining.OVER_FIVE:
            side_min = rules.min_categories_relaxed
            matrix_rule: SituationRule | None = None
        else:
            relaxed = situation.field_position in relaxed_positions
            side_min = rules.min_categories_relaxed if relaxed else rules.min_categories_standard
            matrix_rule = side_rules.get((situation.down, situation.yards_to_go, situation.field_position))

        if matrix_rule is not None:
            violations.extend(_check_matrix_rule(situation, matrix_rule, cats_with_weight, names))

        if not waive_min_categories and len(cats_with_weight) < side_min:
            violations.append(
                Violation(
                    rule_name=names.min_categories,
                    message=(
                        f"Situation {situation.situation_number} has {len(cats_with_weight)} "
                        f"category(ies) with non-zero weight; PNFL requires {side_min}."
                    ),
                    situation_number=situation.situation_number,
                )
            )

    return violations


@dataclass(frozen=True, slots=True)
class _SideRuleNames:
    allowed: RuleName
    mandatory: RuleName
    min_categories: RuleName


_OFFENSE_NAMES = _SideRuleNames(
    allowed=RuleName.OFFENSE_ALLOWED_CATEGORIES,
    mandatory=RuleName.OFFENSE_MANDATORY_CATEGORY,
    min_categories=RuleName.OFFENSE_MIN_CATEGORIES,
)
_DEFENSE_NAMES = _SideRuleNames(
    allowed=RuleName.DEFENSE_ALLOWED_CATEGORIES,
    mandatory=RuleName.DEFENSE_MANDATORY_CATEGORY,
    min_categories=RuleName.DEFENSE_MIN_CATEGORIES,
)


def _check_matrix_rule(
    situation: Situation,
    rule: SituationRule,
    cats_with_weight: frozenset[int],
    names: _SideRuleNames,
) -> list[Violation]:
    """Check allowed-categories and mandatory-alternatives for one situation."""
    violations: list[Violation] = []

    if rule.allowed_categories is not None:
        disallowed = sorted(cats_with_weight - rule.allowed_categories)
        if disallowed:
            violations.append(
                Violation(
                    rule_name=names.allowed,
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
                    rule_name=names.mandatory,
                    message=(
                        f"Situation {situation.situation_number} is missing a mandatory category (one of: {choices})"
                    ),
                    situation_number=situation.situation_number,
                )
            )

    return violations


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
