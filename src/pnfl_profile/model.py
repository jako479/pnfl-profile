"""In-memory wrapper that pairs an fbpro98-profile `Profile` with PNFL rules.

`PnflProfile` is composed of a `Profile` plus a `PnflRules` instance; it does
not inherit from `Profile`. See ARCHITECTURE.md for the reasoning.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Self

from fbpro98_profile import (
    Profile,
    parse_profile,
    read_profile,
    write_profile,
)

from pnfl_profile.rules import PnflRules


@dataclass(frozen=True, slots=True)
class Violation:
    """One PNFL-rule violation reported by `PnflProfile.validate()`.

    `situation_number` is set when the violation is tied to a specific situation
    (1..2520); profile-wide violations (audibles, substitution) set it to None.
    """

    rule_name: str
    message: str
    situation_number: int | None = None


class PnflRuleError(Exception):
    """Raised by `PnflProfile.save()` when validation finds any violations."""

    def __init__(self, violations: tuple[Violation, ...]) -> None:
        self.violations = violations
        super().__init__(f"{len(violations)} PNFL rule violation(s)")


@dataclass(frozen=True, slots=True)
class PnflProfile:
    """A coaching profile bound to a PNFL rule set."""

    profile: Profile
    rules: PnflRules

    @classmethod
    def from_file(cls, path: str, rules: PnflRules) -> Self:
        return cls(profile=read_profile(path), rules=rules)

    @classmethod
    def from_bytes(cls, data: bytes, rules: PnflRules) -> Self:
        return cls(profile=parse_profile(data), rules=rules)

    def validate(self) -> tuple[Violation, ...]:
        """Return every PNFL-rule violation found in the wrapped profile."""
        from pnfl_profile.validators import validate_profile

        return validate_profile(self.profile, self.rules)

    def save(self, path: str) -> None:
        """Validate then write. Raises `PnflRuleError` if any violations exist."""
        violations = self.validate()
        if violations:
            raise PnflRuleError(violations)
        write_profile(self.profile, path)
