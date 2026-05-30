"""In-memory wrapper that pairs an fbpro98-profile `Profile` with PNFL rules.

`PnflProfile` is composed of a `Profile` plus a `PnflRules` instance; it does
not inherit from `Profile`. See ARCHITECTURE.md for the reasoning. Property
forwarders below give the wrapper a `Profile`-shaped API so consumers can
treat a `PnflProfile` as the profile directly without reaching through
`.profile`.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import StrEnum
from typing import ClassVar, Self

from fbpro98_profile import (
    PatSituation,
    Profile,
    ProfileType,
    Situation,
    SubstitutionSettings,
    parse_profile,
    read_profile,
    write_profile,
)

from pnfl_profile.rules import PnflRules

logger = logging.getLogger(__name__)


class RuleName(StrEnum):
    """Identifier for each kind of PNFL-rule violation. Values are stable strings."""

    AUDIBLES_UNCHECKED = "audibles_unchecked"
    OFFENSE_QB_SUBSTITUTION = "offense_qb_substitution"
    OFFENSE_ALLOWED_CATEGORIES = "offense_allowed_categories"
    OFFENSE_MANDATORY_CATEGORY = "offense_mandatory_category"
    OFFENSE_MIN_CATEGORIES = "offense_min_categories"
    DEFENSE_ALLOWED_CATEGORIES = "defense_allowed_categories"
    DEFENSE_MANDATORY_CATEGORY = "defense_mandatory_category"
    DEFENSE_MIN_CATEGORIES = "defense_min_categories"


@dataclass(frozen=True, slots=True)
class Violation:
    """One PNFL-rule violation reported by `PnflProfile.validate()`.

    `situation_number` is set when the violation is tied to a specific situation
    (1..2520); profile-wide violations (audibles, substitution) set it to None.
    """

    rule_name: RuleName
    message: str
    situation_number: int | None = None


@dataclass(frozen=True, slots=True)
class PnflProfile:
    """A coaching profile bound to a PNFL rule set."""

    NUMBER_SITUATIONS: ClassVar[int] = Profile.NUMBER_SITUATIONS
    NUMBER_PAT_SITUATIONS: ClassVar[int] = Profile.NUMBER_PAT_SITUATIONS
    FIELD_GOAL_RANGE_MIN: ClassVar[int] = Profile.FIELD_GOAL_RANGE_MIN
    FIELD_GOAL_RANGE_MAX: ClassVar[int] = Profile.FIELD_GOAL_RANGE_MAX

    profile: Profile
    rules: PnflRules

    @classmethod
    def from_file(cls, path: str, rules: PnflRules) -> Self:
        return cls(profile=read_profile(path), rules=rules)

    @classmethod
    def from_bytes(cls, data: bytes, rules: PnflRules) -> Self:
        return cls(profile=parse_profile(data), rules=rules)

    # ---- Profile forwarders ----

    @property
    def profile_type(self) -> ProfileType:
        return self.profile.profile_type

    @property
    def substitutions(self) -> SubstitutionSettings:
        return self.profile.substitutions

    @property
    def situations(self) -> tuple[Situation, ...]:
        return self.profile.situations

    @property
    def pat_situations(self) -> tuple[PatSituation, ...]:
        return self.profile.pat_situations

    @property
    def field_goal_range(self) -> int:
        return self.profile.field_goal_range

    @property
    def use_audibles(self) -> bool:
        return self.profile.use_audibles

    @property
    def is_offense(self) -> bool:
        return self.profile.is_offense

    @property
    def is_defense(self) -> bool:
        return self.profile.is_defense

    @property
    def stop_clock_situations(self) -> tuple[tuple[int, Situation], ...]:
        return self.profile.stop_clock_situations

    # ---- PNFL rule layer ----

    def validate(self) -> tuple[Violation, ...]:
        """Return every PNFL-rule violation found in the wrapped profile."""
        from pnfl_profile.validators import validate_profile

        return validate_profile(self.profile, self.rules)

    def save(self, path: str) -> tuple[Violation, ...]:
        """Persist the profile; log each violation at WARNING; return the violation tuple.

        The file is written regardless of whether the profile satisfies the bound
        PNFL rule set. PNFL violations are logged via this module's logger (one
        `logger.warning` per violation, prefixed with `[situation N]` when tied
        to a specific situation) and returned to the caller. Callers that want
        to gate writes on violations should call `validate()` first and skip
        `save()` if the report is non-empty.
        """
        violations = self.validate()
        for v in violations:
            prefix = f"[situation {v.situation_number}] " if v.situation_number is not None else ""
            logger.warning("%s%s", prefix, v.message)
        write_profile(self.profile, path)
        if violations:
            logger.info("Persisted with %d PNFL rule violation(s)", len(violations))
        return violations
