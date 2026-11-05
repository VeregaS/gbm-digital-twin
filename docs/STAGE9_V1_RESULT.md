# Stage 9 v1 result and boundary follow-up

## Sealed v1 result

Stage 9 v1 was run on the 24-patient development cohort consisting of the
previous Stage 8 development cases plus the 16 patients exposed during Stage 8
internal validation.

The sealed Stage 9 v1 artifact reported:

- selected candidate:
  `stage9-delayed-transfer-1-half-life-60d-visibility-1`;
- mean Dice: `0.678621`;
- mean Dice delta vs persistence: `-0.014575`;
- mean Dice gain vs exact Stage 8 control: `+0.010680`;
- catastrophic failures: `2`, unchanged from the Stage 8 control;
- regression-subgroup mean delta vs persistence: `-0.034700`;
- 48 reserve patients remained unopened;
- untouched holdout t2 remained unopened.

Artifact SHA-256:

`bc502259e1c1437c13618c987edd0171bee7fefb3a7f03b632555d3851652b7e`

The run was produced from repository commit:

`c286fb1e08de1a19bfab93d04800cb111fc463c5`

## Scientific interpretation

The delayed-response mechanism produced a real development-set improvement
over the exact Stage 8 control, especially in the regression subgroup.

Stage 8 control regression subgroup:

- mean Dice: `0.582459`;
- mean delta vs persistence: `-0.059449`.

Stage 9 selected delayed-response model:

- mean Dice: `0.607207`;
- mean delta vs persistence: `-0.034700`.

Thus the mechanism improves the failure mode it was introduced to address, but
it still does not beat persistence overall or within the regression subgroup.

Two catastrophic cases remain, so the v1 model is not ready for untouched
holdout evaluation.

## Why a boundary follow-up is required

The timescale phase was monotonic over the tested grid:

- 14 d: mean Dice `0.669295`;
- 30 d: mean Dice `0.673983`;
- 60 d: mean Dice `0.678621`.

The selected value, 60 d, was the largest tested half-life. Therefore the
timescale optimum was not bracketed.

The transfer and visibility optima also occurred at 1.0, but those are natural
physical bounds and cannot be increased.

Before consuming new reserve patients, Stage 9.1 tests only:

- 60 d;
- 90 d;
- 120 d.

The transfer and visibility sensitivity grids remain unchanged.

## Stop rule

120 d is deliberately treated as a diagnostic upper bound.

If 60 or 90 d wins, the delayed-response timescale is bracketed well enough to
seal the next candidate.

If 120 d wins, do **not** keep extending the half-life. Interpret that result
as evidence that the current damaged compartment is functioning as a nearly
persistent occupancy / growth-suppression state rather than a well-identified
clearance process. The next model change should then address state semantics or
the observation model instead of performing another half-life sweep.

## Leakage status

Stage 9.1 uses only the same already exposed 24 development patients.

No reserve t2 and no untouched-holdout t2 may be loaded during this follow-up.
