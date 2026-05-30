"""PNFL coaching-profile rule definitions.

Rule data is decoupled from the validators that consume it. The current PNFL
rule set is published in `PNFL_RULES`; alternate rule sets (other seasons,
custom variants for testing) can be constructed by composing the same types.

Source: https://pnfl.biz/messageboard/viewtopic.php?f=18&t=28
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from fbpro98_profile import (
    Down,
    FieldPosition,
    SubstitutionPair,
    YardsToGo,
)

# ---------------------------------------------------------------------------
# Play-category codes (mirrors fbpro98-profile's prf.md section 2.3.2)
# ---------------------------------------------------------------------------

GOAL_LINE_RUN: Final = 0x00
RAZZLE_DAZZLE_RUN: Final = 0x01
RUN_LEFT: Final = 0x02
RUN_MIDDLE: Final = 0x03
RUN_RIGHT: Final = 0x04
GOAL_LINE_PASS: Final = 0x05
RAZZLE_DAZZLE_PASS: Final = 0x06
PASS_LONG_LEFT: Final = 0x07
PASS_LONG_MIDDLE: Final = 0x08
PASS_LONG_RIGHT: Final = 0x09
PASS_MEDIUM_LEFT: Final = 0x0A
PASS_MEDIUM_MIDDLE: Final = 0x0B
PASS_MEDIUM_RIGHT: Final = 0x0C
PASS_SHORT_LEFT: Final = 0x0D
PASS_SHORT_MIDDLE: Final = 0x0E
PASS_SHORT_RIGHT: Final = 0x0F
FIELD_GOAL_PAT: Final = 0x10
FAKE_FIELD_GOAL_RUN: Final = 0x11
FAKE_FIELD_GOAL_PASS: Final = 0x12
PUNT: Final = 0x13
FAKE_PUNT_RUN: Final = 0x14
FAKE_PUNT_PASS: Final = 0x15
RUN_CLOCK: Final = 0x16
RUN_RANDOM: Final = 0x17
PASS_LONG_RANDOM: Final = 0x18
PASS_MEDIUM_RANDOM: Final = 0x19
PASS_SHORT_RANDOM: Final = 0x1A

OFFENSE_CATEGORIES: Final[frozenset[int]] = frozenset(range(0x00, 0x1B))
DEFENSE_CATEGORIES: Final[frozenset[int]] = frozenset(range(0x00, 0x16))

# Defense doesn't distinguish pass direction; all three direction codes count
# as the same conceptual category.
PASS_LONG_ANY: Final[frozenset[int]] = frozenset({PASS_LONG_LEFT, PASS_LONG_MIDDLE, PASS_LONG_RIGHT})
PASS_MEDIUM_ANY: Final[frozenset[int]] = frozenset({PASS_MEDIUM_LEFT, PASS_MEDIUM_MIDDLE, PASS_MEDIUM_RIGHT})
PASS_SHORT_ANY: Final[frozenset[int]] = frozenset({PASS_SHORT_LEFT, PASS_SHORT_MIDDLE, PASS_SHORT_RIGHT})

# Min-categories waiver: skipped when every category with weight > 0 is in the
# side's exempt set. Defense has no RUN_CLOCK (0x16 is outside DEFENSE_CATEGORIES).
OFFENSE_EXEMPT_CATEGORIES: Final[frozenset[int]] = frozenset({FIELD_GOAL_PAT, PUNT, RUN_CLOCK})
DEFENSE_EXEMPT_CATEGORIES: Final[frozenset[int]] = frozenset({FIELD_GOAL_PAT, PUNT})


# ---------------------------------------------------------------------------
# Per-situation rule type
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SituationRule:
    """Play-category constraints for one game situation key.

    `allowed_categories=None` means any category is permitted. `mandatory_alternatives`
    is a tuple of category sets: at least one category from each set must appear with
    weight > 0 (e.g., `({PASS_SHORT_RIGHT},)` requires PSR; on defense the rule
    `PASS_LONG mandatory` is encoded as `(PASS_LONG_ANY,)` since any of the three
    direction codes satisfies it).
    """

    allowed_categories: frozenset[int] | None
    mandatory_alternatives: tuple[frozenset[int], ...]


# Keys into the per-situation rule maps. (Down, YardsToGo, FieldPosition) is enough —
# PointSpread doesn't affect PNFL rules, and the time dimension is handled separately
# (rules only apply when minutes_remaining is OVER_FIVE).
SituationKey = tuple[Down, YardsToGo, FieldPosition]


# ---------------------------------------------------------------------------
# Helpers for building the rule matrices
# ---------------------------------------------------------------------------


_BETWEEN_5_5: Final = (FieldPosition.DEF_5_TO_DEF_35, FieldPosition.DEF_35_TO_OFF_35, FieldPosition.OFF_35_TO_OFF_5)
_ALL_FIELD: Final = tuple(FieldPosition)
_DEF_35_TO_OFF_5: Final = (FieldPosition.DEF_35_TO_OFF_35, FieldPosition.OFF_35_TO_OFF_5)


def _key_set(
    down: Down,
    yards: YardsToGo,
    fields: tuple[FieldPosition, ...],
) -> tuple[SituationKey, ...]:
    """Build keys for one (down, yards) across the given field positions, skipping
    structurally-invalid INSIDE_DEF_5 + ≥6 yards-to-go combos."""
    invalid = yards.value >= 2  # SIX_TO_TEN or OVER_TEN
    return tuple((down, yards, fp) for fp in fields if not (invalid and fp == FieldPosition.INSIDE_DEF_5))


def _rule(
    allowed: frozenset[int] | None,
    *,
    mandatory: tuple[frozenset[int], ...] = (),
) -> SituationRule:
    return SituationRule(
        allowed_categories=allowed,
        mandatory_alternatives=mandatory,
    )


def _spread(
    rule: SituationRule,
    keys: tuple[SituationKey, ...],
) -> dict[SituationKey, SituationRule]:
    return {k: rule for k in keys}


# ---------------------------------------------------------------------------
# Offensive rule matrix (minutes_remaining = OVER_FIVE)
# ---------------------------------------------------------------------------

_RUN_LEFT_MIDDLE = frozenset({RUN_LEFT, RUN_MIDDLE})
_RUN_MIDDLE_RIGHT = frozenset({RUN_MIDDLE, RUN_RIGHT})
_RUN_ALL_THREE = frozenset({RUN_LEFT, RUN_MIDDLE, RUN_RIGHT})
_PASS_SL_ML = frozenset({PASS_SHORT_LEFT, PASS_MEDIUM_LEFT})
_PASS_SM_MM = frozenset({PASS_SHORT_MIDDLE, PASS_MEDIUM_MIDDLE})
_GOAL_LINE = frozenset({GOAL_LINE_PASS, GOAL_LINE_RUN})

_OFFENSE_1ST_0_1 = _RUN_LEFT_MIDDLE | _PASS_SL_ML | _GOAL_LINE
_OFFENSE_1ST_2_5_BETWEEN = _RUN_LEFT_MIDDLE | _PASS_SL_ML
_OFFENSE_1ST_2_5_GOALLINES = _RUN_LEFT_MIDDLE | _PASS_SL_ML | _GOAL_LINE
_OFFENSE_1ST_6_10_BETWEEN = frozenset({RUN_MIDDLE}) | _PASS_SL_ML
_OFFENSE_1ST_6_10_OFF5 = _RUN_LEFT_MIDDLE | _PASS_SL_ML | _GOAL_LINE

_OFFENSE_2ND_0_1 = _RUN_LEFT_MIDDLE | _PASS_SM_MM | _GOAL_LINE
_OFFENSE_2ND_2_5_BETWEEN = _RUN_LEFT_MIDDLE | _PASS_SM_MM
_OFFENSE_2ND_2_5_GOALLINES = _RUN_LEFT_MIDDLE | _PASS_SM_MM | _GOAL_LINE
_OFFENSE_2ND_6_10_BETWEEN = _RUN_MIDDLE_RIGHT | _PASS_SM_MM
_OFFENSE_2ND_6_10_OFF5 = _RUN_ALL_THREE | _PASS_SM_MM | _GOAL_LINE

_OFFENSE_3RD_NO_RDP = OFFENSE_CATEGORIES - {RAZZLE_DAZZLE_PASS}


def _build_offense_rules() -> dict[SituationKey, SituationRule]:
    """Per `https://pnfl.biz/messageboard/viewtopic.php?f=18&t=28`, offensive rules for minutes_remaining > 5."""
    rules: dict[SituationKey, SituationRule] = {}

    # 1st down ----------------------------------------------------------------
    rules.update(
        _spread(
            _rule(_OFFENSE_1ST_0_1),
            _key_set(Down.FIRST, YardsToGo.ZERO_TO_ONE, _ALL_FIELD),
        )
    )
    rules.update(
        _spread(
            _rule(_OFFENSE_1ST_2_5_GOALLINES),
            _key_set(Down.FIRST, YardsToGo.TWO_TO_FIVE, (FieldPosition.INSIDE_DEF_5,)),
        )
    )
    rules.update(
        _spread(
            _rule(_OFFENSE_1ST_2_5_BETWEEN),
            _key_set(Down.FIRST, YardsToGo.TWO_TO_FIVE, _BETWEEN_5_5),
        )
    )
    rules.update(
        _spread(
            _rule(_OFFENSE_1ST_2_5_GOALLINES),
            _key_set(Down.FIRST, YardsToGo.TWO_TO_FIVE, (FieldPosition.INSIDE_OFF_5,)),
        )
    )
    rules.update(
        _spread(
            _rule(_OFFENSE_1ST_6_10_BETWEEN),
            _key_set(Down.FIRST, YardsToGo.SIX_TO_TEN, _BETWEEN_5_5),
        )
    )
    rules.update(
        _spread(
            _rule(_OFFENSE_1ST_6_10_OFF5),
            _key_set(Down.FIRST, YardsToGo.SIX_TO_TEN, (FieldPosition.INSIDE_OFF_5,)),
        )
    )
    rules.update(
        _spread(
            _rule(None),  # >10 yards: any category
            _key_set(Down.FIRST, YardsToGo.OVER_TEN, (*_BETWEEN_5_5, FieldPosition.INSIDE_OFF_5)),
        )
    )

    # 2nd down ----------------------------------------------------------------
    rules.update(
        _spread(
            _rule(_OFFENSE_2ND_0_1),
            _key_set(Down.SECOND, YardsToGo.ZERO_TO_ONE, _ALL_FIELD),
        )
    )
    rules.update(
        _spread(
            _rule(_OFFENSE_2ND_2_5_GOALLINES),
            _key_set(Down.SECOND, YardsToGo.TWO_TO_FIVE, (FieldPosition.INSIDE_DEF_5,)),
        )
    )
    rules.update(
        _spread(
            _rule(_OFFENSE_2ND_2_5_BETWEEN),
            _key_set(Down.SECOND, YardsToGo.TWO_TO_FIVE, _BETWEEN_5_5),
        )
    )
    rules.update(
        _spread(
            _rule(_OFFENSE_2ND_2_5_GOALLINES),
            _key_set(Down.SECOND, YardsToGo.TWO_TO_FIVE, (FieldPosition.INSIDE_OFF_5,)),
        )
    )
    rules.update(
        _spread(
            _rule(_OFFENSE_2ND_6_10_BETWEEN),
            _key_set(Down.SECOND, YardsToGo.SIX_TO_TEN, _BETWEEN_5_5),
        )
    )
    rules.update(
        _spread(
            _rule(_OFFENSE_2ND_6_10_OFF5),
            _key_set(Down.SECOND, YardsToGo.SIX_TO_TEN, (FieldPosition.INSIDE_OFF_5,)),
        )
    )
    rules.update(
        _spread(
            _rule(None),
            _key_set(Down.SECOND, YardsToGo.OVER_TEN, (*_BETWEEN_5_5, FieldPosition.INSIDE_OFF_5)),
        )
    )

    # 3rd down ----------------------------------------------------------------
    rules.update(
        _spread(
            _rule(_OFFENSE_3RD_NO_RDP),
            _key_set(Down.THIRD, YardsToGo.ZERO_TO_ONE, _ALL_FIELD),
        )
    )
    rules.update(
        _spread(
            _rule(None),
            _key_set(Down.THIRD, YardsToGo.TWO_TO_FIVE, (FieldPosition.INSIDE_DEF_5,)),
        )
    )
    rules.update(
        _spread(
            _rule(None, mandatory=(frozenset({PASS_SHORT_RIGHT}),)),
            _key_set(Down.THIRD, YardsToGo.TWO_TO_FIVE, _BETWEEN_5_5),
        )
    )
    rules.update(
        _spread(
            _rule(None),
            _key_set(Down.THIRD, YardsToGo.TWO_TO_FIVE, (FieldPosition.INSIDE_OFF_5,)),
        )
    )
    rules.update(
        _spread(
            _rule(None, mandatory=(frozenset({PASS_MEDIUM_RIGHT}),)),
            _key_set(Down.THIRD, YardsToGo.SIX_TO_TEN, _BETWEEN_5_5),
        )
    )
    rules.update(
        _spread(
            _rule(None),
            _key_set(Down.THIRD, YardsToGo.SIX_TO_TEN, (FieldPosition.INSIDE_OFF_5,)),
        )
    )
    rules.update(
        _spread(
            _rule(None),
            _key_set(Down.THIRD, YardsToGo.OVER_TEN, (FieldPosition.DEF_5_TO_DEF_35,)),
        )
    )
    rules.update(
        _spread(
            _rule(None, mandatory=(frozenset({PASS_LONG_RIGHT}),)),
            _key_set(Down.THIRD, YardsToGo.OVER_TEN, _DEF_35_TO_OFF_5),
        )
    )
    rules.update(
        _spread(
            _rule(None),
            _key_set(Down.THIRD, YardsToGo.OVER_TEN, (FieldPosition.INSIDE_OFF_5,)),
        )
    )

    return rules


# ---------------------------------------------------------------------------
# Defensive rule matrix (minutes_remaining = OVER_FIVE)
# ---------------------------------------------------------------------------


def _build_defense_rules() -> dict[SituationKey, SituationRule]:
    """Per `https://pnfl.biz/messageboard/viewtopic.php?f=18&t=28`, defensive
    mandatory categories on 3rd down."""
    rules: dict[SituationKey, SituationRule] = {}
    rules.update(
        _spread(
            _rule(None, mandatory=(PASS_SHORT_ANY,)),
            _key_set(Down.THIRD, YardsToGo.TWO_TO_FIVE, _BETWEEN_5_5),
        )
    )
    rules.update(
        _spread(
            _rule(None, mandatory=(PASS_MEDIUM_ANY,)),
            _key_set(Down.THIRD, YardsToGo.SIX_TO_TEN, _BETWEEN_5_5),
        )
    )
    rules.update(
        _spread(
            _rule(None, mandatory=(PASS_LONG_ANY,)),
            _key_set(Down.THIRD, YardsToGo.OVER_TEN, _DEF_35_TO_OFF_5),
        )
    )
    return rules


# ---------------------------------------------------------------------------
# Top-level rule container
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PnflRules:
    """PNFL coaching-profile validation rule set.

    Pass instances to `PnflProfile` to bind a profile to a particular rule set
    (e.g., a future season's rules, or a custom variant for tests).

    `*_relaxed_field_positions` names the field positions where the standard
    3-category minimum drops to 2 (the "own 5-yard line" exception). Field
    position is encoded from the offense's perspective in the .prf format,
    so the offense's own 5 = `INSIDE_OFF_5` and the defense's own 5 (defense
    backed up to its goal line, offense in red zone) = `INSIDE_DEF_5`.
    """

    audibles_allowed: bool
    offense_qb_substitution: SubstitutionPair | None
    offense_situations: dict[SituationKey, SituationRule]
    defense_situations: dict[SituationKey, SituationRule]
    offense_relaxed_field_positions: frozenset[FieldPosition]
    defense_relaxed_field_positions: frozenset[FieldPosition]
    min_categories_relaxed: int  # Usually 2
    min_categories_standard: int  # Usually 3
    offense_exempt_categories: frozenset[int]  # Waive min-categories when every non-zero category is in this set
    defense_exempt_categories: frozenset[int]


PNFL_RULES: Final[PnflRules] = PnflRules(
    audibles_allowed=False,
    offense_qb_substitution=SubstitutionPair(out_percent=75, in_percent=80),
    offense_situations=_build_offense_rules(),
    defense_situations=_build_defense_rules(),
    offense_relaxed_field_positions=frozenset({FieldPosition.INSIDE_OFF_5}),
    defense_relaxed_field_positions=frozenset({FieldPosition.INSIDE_DEF_5}),
    min_categories_relaxed=2,
    min_categories_standard=3,
    offense_exempt_categories=OFFENSE_EXEMPT_CATEGORIES,
    defense_exempt_categories=DEFENSE_EXEMPT_CATEGORIES,
)
