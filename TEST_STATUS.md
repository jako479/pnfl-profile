# pnfl-profile — Test Status

**Test Status: Tests Complete for Current Rule Coverage**

## Covered by automated tests

- Universal rules — audibles checked / unchecked, on both offense and defense.
- Offensive QB substitution — passing `75/80`, violating any other pair, ignored on defense.
- Min-categories — standard 3-category minimum on both sides; relaxed 2-category exception for offense's INSIDE_OFF_5 and defense's INSIDE_DEF_5; allowed/mandatory still apply at relaxed cells.
- Time / down gating — rules waived when minutes-remaining is not `OVER_FIVE`; 4th down never fires category rules.
- Offensive matrix — 1st-down 0-1 allowed set, 1st-down 6-10 between-5s restriction (no RL), 1st->10 unrestricted, 2nd-down 6-10 between-5s restriction (no RL, RR allowed), 2nd-down 6-10 INSIDE_OFF_5 allowed set, 3rd-down 0-1 no RDP, 3rd-down 2-5 PSR mandatory only between-5s, 3rd-down 6-10 PMR mandatory between-5s, 3rd->10 PLR mandatory only DEF_35-OFF_5.
- Defensive matrix — 3rd-2-5 between-5s PS mandatory (any short-pass direction satisfies), 3rd-6-10 between-5s PM mandatory, 3rd->10 DEF_35-OFF_5 PL mandatory, free DEF_5-DEF_35 zone.
- Point-spread invariance — same violation fires for the same (down, yards, field) under different point-spread buckets.
- `PnflProfile` API — constructor pairing, validate returning tuple, from_file/from_bytes roundtrip, save-with-violations raises and preserves any existing file at the path, save-clean writes a profile that fbpro98-profile reloads to equality.
- Real-profile baselines — `TST-OFF1.prf` and `TST-DEF1.prf` load and produce pinned violation counts (17 and 7 respectively) so validator or rule-data regressions surface immediately.

## Needs tests

- Once 4th-down or punt/FG rules are added, mirror the offensive/defensive matrix-coverage pattern.
- Once additional rule sets exist (e.g. `PNFL_RULES_2027`), add a smoke test loading a real profile under each.
