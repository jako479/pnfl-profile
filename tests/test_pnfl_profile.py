"""Tests for the `PnflProfile` wrapper itself: construction, I/O, save semantics."""

from __future__ import annotations

import logging
from dataclasses import replace
from pathlib import Path

import pytest
from fbpro98_profile import Profile, read_profile

from pnfl_profile import (
    PNFL_RULES,
    PnflProfile,
    PnflRuleWarning,
)


def test_constructor_pairs_profile_with_rules(offense_profile: Profile) -> None:
    pp = PnflProfile(profile=offense_profile, rules=PNFL_RULES)
    assert pp.profile is offense_profile
    assert pp.rules is PNFL_RULES


def test_validate_returns_tuple(offense_profile: Profile) -> None:
    violations = PnflProfile(profile=offense_profile, rules=PNFL_RULES).validate()
    assert isinstance(violations, tuple)
    assert violations == ()


def test_validate_returns_violations_when_dirty(offense_profile: Profile) -> None:
    profile = replace(offense_profile, use_audibles=True)
    violations = PnflProfile(profile=profile, rules=PNFL_RULES).validate()
    assert any(v.rule_name == "audibles_unchecked" for v in violations)


def test_from_file_roundtrip(offense_profile: Profile, tmp_path: Path) -> None:
    """from_file → validate path: write a compliant profile, load it, validate clean."""
    out_path = tmp_path / "ROUND.prf"
    PnflProfile(profile=offense_profile, rules=PNFL_RULES).save(str(out_path))

    loaded = PnflProfile.from_file(str(out_path), PNFL_RULES)
    assert loaded.validate() == ()


def test_from_bytes_loads_profile(offense_profile: Profile, tmp_path: Path) -> None:
    out_path = tmp_path / "BYTES.prf"
    PnflProfile(profile=offense_profile, rules=PNFL_RULES).save(str(out_path))

    data = out_path.read_bytes()
    loaded = PnflProfile.from_bytes(data, PNFL_RULES)
    assert loaded.validate() == ()


def test_save_returns_empty_when_compliant(offense_profile: Profile, tmp_path: Path) -> None:
    out_path = tmp_path / "OK.prf"
    result = PnflProfile(profile=offense_profile, rules=PNFL_RULES).save(str(out_path))
    assert result == ()
    assert out_path.exists()
    reloaded = read_profile(str(out_path))
    assert reloaded == offense_profile


def test_save_persists_despite_violations(
    offense_profile: Profile,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    bad = replace(offense_profile, use_audibles=True)
    pp = PnflProfile(profile=bad, rules=PNFL_RULES)
    out_path = tmp_path / "BAD.prf"

    with pytest.warns(PnflRuleWarning) as captured, caplog.at_level(logging.INFO, logger="pnfl_profile.model"):
        result = pp.save(str(out_path))

    # File IS written despite violations.
    assert out_path.exists()
    assert any(v.rule_name == "audibles_unchecked" for v in result)
    assert any("audibles" in str(w.message).lower() for w in captured.list)
    assert any(
        r.levelno == logging.INFO and "Persisted with" in r.message and "violation" in r.message for r in caplog.records
    )


def test_save_overwrites_existing_with_violations(offense_profile: Profile, tmp_path: Path) -> None:
    """Warn-and-persist policy: an existing file is replaced even when violations are present."""
    out_path = tmp_path / "OVERWRITTEN.prf"
    out_path.write_bytes(b"sentinel")
    bad = replace(offense_profile, use_audibles=True)

    with pytest.warns(PnflRuleWarning):
        PnflProfile(profile=bad, rules=PNFL_RULES).save(str(out_path))

    assert out_path.read_bytes() != b"sentinel"
