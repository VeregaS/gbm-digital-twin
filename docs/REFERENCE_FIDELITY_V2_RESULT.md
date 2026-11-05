# Reference Fidelity v2 — sealed development result

## Status

Reference Fidelity v2 is complete on the same 24 already exposed development
patients used for Stage 9. It is a development diagnostic, not independent
validation.

Project commit used for the run:

`89fc83e35c09d58c46f283275ed3316d6498d0ab`

Pinned TumorTwin commit:

`bedf90a6d47ba48cf5cdb25901967d84730061d1`

Sealed Stage 9 v2 artifact SHA-256 referenced by the run:

`f4b7270f545753278b0381876906a3820a6f35d9fdde9b82a3cbb4e227a75f5e`

## Leakage contract

The run preserved the predefined boundary:

- development patients only: `24`;
- ADC paired subset: `9`;
- ADC used at t0 and t1 only;
- t2 ADC loaded: `false`;
- raw FLAIR thresholded: `false`;
- t2 GTV used only after the reference forecast was frozen;
- reserve patients were not opened;
- untouched CFB holdout was not opened.

The ADC-eligible development patients were:

`25, 45, 65, 70, 76, 99, 112, 120, 214`.

## Experiment A — ROI-cropped GTV reference

`tumortwin-lm-roi`, all 24 patients:

- mean Dice: `0.636752`;
- mean persistence Dice: `0.693196`;
- mean delta vs persistence: `-0.056445`;
- mean delta vs Stage 9: `-0.044652`;
- mean HD95: `11.6469 mm`;
- mean relative volume error: `1.810949`;
- better / equal / worse than persistence: `4 / 6 / 14`;
- catastrophic failures: `5`.

Reference benchmark v1 TumorTwin LM had mean Dice `0.637488`. The tumor-centric
ROI therefore did not materially improve the reference result.

## Experiment B — paired ADC diagnostic

The comparison is restricted to exactly the same 9 patients.

### ROI-GTV branch

`tumortwin-lm-roi-adc-paired-subset`:

- mean Dice: `0.575452`;
- mean persistence Dice: `0.646785`;
- mean delta vs persistence: `-0.071333`;
- mean delta vs Stage 9: `-0.068437`;
- mean HD95: `9.8016 mm`;
- mean relative volume error: `3.377502`;
- catastrophic failures: `3`.

### ADC-derived enhancing-cellularity branch

`tumortwin-adc-lm-roi`:

- mean Dice: `0.393779`;
- mean persistence Dice: `0.646785`;
- mean delta vs persistence: `-0.253006`;
- mean delta vs Stage 9: `-0.250110`;
- mean HD95: `9.8588 mm`;
- mean relative volume error: `1.428942`;
- better / worse than persistence: `2 / 7`;
- catastrophic failures: `5`.

The ADC-derived enhancing-cellularity pipeline therefore did not satisfy the
predefined advancement condition. It substantially reduced paired mean Dice
and increased catastrophic failures from `3` to `5` relative to the paired
ROI-GTV branch.

This negative result does not establish that ADC is uninformative in GBM. It
shows only that the tested TumorTwin-style enhancing-cellularity transform,
with the currently available CFB inputs and fixed predeclared threshold, does
not improve this forecasting task.

## Decision

Neither Reference Fidelity v2 branch met its predefined advancement condition:

1. ROI cropping did not materially improve the GTV reference;
2. ADC did not improve the paired subset without increasing catastrophic
   failures.

Therefore the predefined fallback is activated:

**proceed to Stage 10 decoupled visible-clearance / inert-occupancy diagnostic
on the same 24 exposed development patients.**

No reserve patient or untouched holdout patient may be opened for Stage 10
model-family selection.
