# pnfl-profile — Test Status

**Test Status: Tests Complete for Current Rule Coverage**

## Covered by automated tests

- Universal rules — audibles checked / unchecked, on both offense and defense.
- Offensive QB substitution — passing `75/80`, violating any other pair, ignored on defense.
- Min-categories — standard 3-category minimum on both sides; relaxed 2-category exception for offense's INSIDE_OFF_5 and defense's INSIDE_DEF_5 (above 5:00); 2-category minimum anywhere when ≤5:00 remain.
- Time / down gating — matrix rules (allowed/mandatory) only fire above 5:00; ≤5:00 enforces only the 2-category minimum.
- 4th-down kick exemption — PUNT or FIELD_GOAL_PAT with weight > 0 waives the category-count check at any time; without a kick, the standard count check still applies.
- Offensive matrix — 1st-down 0-1 allowed set, 1st-down 6-10 between-5s restriction (no RL), 1st->10 unrestricted, 2nd-down 6-10 between-5s restriction (no RL, RR allowed), 2nd-down 6-10 INSIDE_OFF_5 allowed set, 3rd-down 0-1 no RDP, 3rd-down 2-5 PSR mandatory only between-5s, 3rd-down 6-10 PMR mandatory between-5s, 3rd->10 PLR mandatory only DEF_35-OFF_5.
- Defensive matrix — 3rd-2-5 between-5s PS mandatory (any short-pass direction satisfies), 3rd-6-10 between-5s PM mandatory, 3rd->10 DEF_35-OFF_5 PL mandatory, free DEF_5-DEF_35 zone.
- Point-spread invariance — same violation fires for the same (down, yards, field) under different point-spread buckets.
- `PnflProfile` API — constructor pairing, validate returning tuple, from_file/from_bytes roundtrip, save-clean writes a profile that fbpro98-profile reloads to equality, save-with-violations emits `PnflRuleWarning` (asserted via `pytest.warns`), persists the file regardless, returns the violation tuple, and logs a `Persisted with N violation(s)` INFO summary line.
- Real-profile baselines — `TST-OFF1.prf` and `TST-DEF1.prf` load and produce pinned violation counts (138 and 7 respectively) so validator or rule-data regressions surface immediately.
- Matrix-key satisfiability loop — parametrized test over every key in `PNFL_RULES.offense_situations` and `PNFL_RULES.defense_situations` asserts a compliant profile fires no violations at that key.

## Needs tests

- Once additional rule sets exist (e.g. `PNFL_RULES_2027`), add a smoke test loading a real profile under each.
