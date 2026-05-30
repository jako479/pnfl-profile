# PNFL Coaching-Profile Rules

The complete list of PNFL rules enforced by `validate_profile`. Source: the league's [coaching-profile rules thread](https://pnfl.biz/messageboard/viewtopic.php?f=18&t=28).

Field position is encoded from the offense's perspective in the `.prf` format. The "own 5-yard line" therefore resolves to `INSIDE_OFF_5` for offense and `INSIDE_DEF_5` for defense.

## Universal

- **Audibles unchecked.** Both offense and defense profiles must save with audibles off.

## Offensive

- **QB substitution = 75/80.** Quarterback substitution `out_percent` must be 75 and `in_percent` must be 80.

### Allowed-category matrix (above 5:00)

For each `(Down, YardsToGo, FieldPosition)`, every play category used with weight > 0 must come from the listed set. Cells not listed below allow any category. Applies only when `MinutesRemaining == OVER_FIVE`.

- **1st down, 0-1 yds, anywhere:** Run Left, Run Middle, Pass Short Left, Pass Medium Left, Goal Line Run, Goal Line Pass
- **1st down, 2-5 yds, between the 5s:** Run Left, Run Middle, Pass Short Left, Pass Medium Left
- **1st down, 2-5 yds, inside either 5:** add Goal Line Run, Goal Line Pass
- **1st down, 6-10 yds, between the 5s:** Run Middle, Pass Short Left, Pass Medium Left
- **1st down, 6-10 yds, inside own 5:** Run Left, Run Middle, Pass Short Left, Pass Medium Left, Goal Line Run, Goal Line Pass
- **1st down, >10 yds:** any
- **2nd down, 0-1 yds, anywhere:** Run Left, Run Middle, Pass Short Middle, Pass Medium Middle, Goal Line Run, Goal Line Pass
- **2nd down, 2-5 yds, between the 5s:** Run Left, Run Middle, Pass Short Middle, Pass Medium Middle
- **2nd down, 2-5 yds, inside either 5:** add Goal Line Run, Goal Line Pass
- **2nd down, 6-10 yds, between the 5s:** Run Middle, Run Right, Pass Short Middle, Pass Medium Middle
- **2nd down, 6-10 yds, inside own 5:** Run Left, Run Middle, Run Right, Pass Short Middle, Pass Medium Middle, Goal Line Run, Goal Line Pass
- **2nd down, >10 yds:** any
- **3rd down, 0-1 yds:** any *except* Razzle Dazzle Pass

### Mandatory-category matrix (above 5:00)

At least one play category used (weight > 0) must be from each listed set. Applies only when `MinutesRemaining == OVER_FIVE`.

- **3rd down, 2-5 yds, between the 5s:** Pass Short Right
- **3rd down, 6-10 yds, between the 5s:** Pass Medium Right
- **3rd down, >10 yds, opponent-35-to-own-5:** Pass Long Right

## Defensive

### Mandatory-category matrix (above 5:00)

At least one play category used (weight > 0) must be from each listed set.

- **3rd down, 2-5 yds, between the 5s:** any of Pass Short Left, Pass Short Middle, Pass Short Right
- **3rd down, 6-10 yds, between the 5s:** any of Pass Medium Left, Pass Medium Middle, Pass Medium Right
- **3rd down, >10 yds, opponent-35-to-own-5:** any of Pass Long Left, Pass Long Middle, Pass Long Right

## Category-count minimum

Applies to both offense and defense, all matrix cells, all situations.

- **Standard:** at least **3** distinct categories with weight > 0.
- **Lowered to 2** in any of these cases:
  - `MinutesRemaining != OVER_FIVE` (the half is at 5:00 or less) — any field, any down.
  - `MinutesRemaining == OVER_FIVE` and the team is inside its own 5-yard line.
- **Waived** when every category with weight > 0 is in the exempt set: offense `{FG, PUNT, RUN_CLOCK}`, defense `{FG, PUNT}`. Any down, any time. Add a non-exempt category and the minimum applies (exempt categories count toward it). Matrix rules still fire.

## Matrix rules vs. category-count

Matrix rules (allowed-category and mandatory-category cells) only apply when `MinutesRemaining == OVER_FIVE`. When ≤5:00 remain, only the category-count minimum is enforced.
