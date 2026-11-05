# Stage 9 v2 result — boundary stop triggered

## Sealed result

Stage 9 v2 repeated delayed-response selection on the same 24 already exposed
development patients and extended only the damaged-compartment half-life grid.

The run was produced from repository commit:

`91501c96602dfed1e7ab0251518256984d8aa5d9`

The repository was clean.

Selected candidate:

`stage9-delayed-transfer-1-half-life-120d-visibility-1`

Aggregate metrics:

- mean Dice: `0.681404`;
- median Dice: `0.731461`;
- mean Dice delta vs persistence: `-0.011792`;
- mean Dice gain vs exact Stage 8 control: `+0.013462`;
- mean HD95: `11.2522 mm`;
- mean relative volume error: `0.950507`;
- better / equal / worse than persistence: `6 / 10 / 8`;
- catastrophic failures: `2`.

Exact Stage 8 control on the same 24 patients:

- mean Dice: `0.667942`;
- mean Dice delta vs persistence: `-0.025255`;
- mean HD95: `11.4887 mm`;
- mean relative volume error: `1.238834`;
- catastrophic failures: `2`.

Artifact SHA-256:

`f4b7270f545753278b0381876906a3820a6f35d9fdde9b82a3cbb4e227a75f5e`

The uploaded checksum matched the JSON bytes exactly.

## Timescale boundary diagnostic

The development-set mean Dice remained monotonic across the expanded grid:

- 60 d: `0.678621`;
- 90 d: `0.680696`;
- 120 d: `0.681404`.

The 120-day candidate was selected in all 24 leave-one-patient-out folds of the
timescale phase.

The same final `transfer=1, visibility=1` structure was also selected in all
24 leave-one-patient-out folds of the transfer and visibility phases.

Therefore the Stage 9.1 stop rule is triggered:

> Do not extend the delayed-damage half-life search beyond 120 days.

The current parameter no longer behaves like a well-bracketed clearance
timescale. The development data prefer a damaged state that remains present
for most of the forecast horizon.

## Where the gain comes from

The main gain remains concentrated in the regression subgroup.

Stage 8 control, regression patients:

- n = `11`;
- mean Dice = `0.582459`;
- mean delta vs persistence = `-0.059449`.

Stage 9 v2, regression patients:

- n = `11`;
- mean Dice = `0.612796`;
- mean delta vs persistence = `-0.029112`.

The regression-subgroup Dice gain over the exact Stage 8 control is therefore
approximately `+0.03034`.

Growth patients are essentially unchanged/slightly worse:

- Stage 8 control mean Dice = `0.682868`;
- Stage 9 v2 mean Dice = `0.681540`.

Stable patients are effectively unchanged.

This pattern supports the treatment-memory hypothesis, but not the current
single-compartment semantics.

## Remaining catastrophic failures

Two catastrophic failures remain under the predefined threshold
`delta_vs_persistence < -0.10`:

### Patient 108

- persistence Dice: `0.641058`;
- Stage 9 v2 Dice: `0.461433`;
- delta: `-0.179625`;
- observed t2 volume: `8.112 cm3`;
- predicted t2 volume: `27.048 cm3`.

### Patient 205

- persistence Dice: `0.852490`;
- Stage 9 v2 Dice: `0.660450`;
- delta: `-0.192041`;
- observed t2 volume: `11.056 cm3`;
- predicted t2 volume: `22.400 cm3`.

The 120-day state reduces overgrowth relative to shorter half-lives but does
not resolve it.

## Mechanistic interpretation

In the current Stage 9 equations the same damaged state `d` has three roles:

1. it contributes to MRI-visible density;
2. it occupies logistic carrying capacity;
3. its exponential decay simultaneously removes visible signal and releases
   carrying capacity.

A longer half-life therefore does more than delay radiographic clearance: it
also prevents viable regrowth for longer.

Because the best tested half-life again sits at the diagnostic ceiling, the
next experiment must decouple **visible damaged-tissue clearance** from
**persistent post-treatment occupancy / growth suppression**.

The project must not interpret 120 days as a patient-independent biological
half-life estimate.

## Leakage status

- development patients: `24`;
- reserve patients still unopened: `48`;
- reserve t2 loaded: `false`;
- untouched holdout t2 loaded: `false`.

No Stage 9 reserve validation should be run from this v2 candidate. The next
model-family diagnostic must first be completed on the same exposed
development cohort.
