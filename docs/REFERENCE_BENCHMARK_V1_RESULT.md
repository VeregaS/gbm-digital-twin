# Published reference benchmark v1 — result

## Scope

The benchmark compared the current Stage 9 development result with the pinned
published TumorTwin implementation on the same 24 already exposed CFB
development patients.

Pinned TumorTwin commit:

`bedf90a6d47ba48cf5cdb25901967d84730061d1`

The benchmark artifact was produced from a clean project tree at:

`3143c8050b219ca5cffe9eb599093fc048c8c3ce`

This checkpoint remained development-only. Reserve and untouched-holdout
patients were not opened by the reference benchmark.

## Aggregate result

Persistence on the 24-patient cohort:

- mean Dice: `0.693196`.

Current Stage 9 v2 on the same cohort:

- mean Dice: approximately `0.681404`;
- mean delta vs persistence: approximately `-0.011792`;
- catastrophic failures: `2`.

TumorTwin with frozen Stage 8/9 D and rho:

- mean Dice: `0.629097`;
- mean delta vs persistence: `-0.064100`;
- mean delta vs Stage 9: `-0.052307`;
- mean HD95: `12.8172 mm`;
- mean relative volume error: `2.486804`;
- better / equal / worse than persistence: `3 / 6 / 15`;
- catastrophic failures: `5`.

TumorTwin with upstream Levenberg-Marquardt calibration on t0 -> t1:

- mean Dice: `0.637488`;
- mean delta vs persistence: `-0.055708`;
- mean delta vs Stage 9: `-0.043916`;
- mean HD95: `11.5988 mm`;
- mean relative volume error: `1.797364`;
- better / equal / worse than persistence: `4 / 6 / 14`;
- catastrophic failures: `5`.

Artifact SHA-256:

`d97737c8a0a62b46a506c0106e07800bc7c2dbac1a80cb27697f6d3e34490677`

The checksum supplied with the artifact matches the JSON bytes.

## What this result establishes

The published TumorTwin reaction-diffusion solver does not improve the current
CFB forecast merely by replacing the local numerical implementation while
keeping the same patient-specific D/rho.

The upstream LM inverse problem improves the TumorTwin result relative to its
frozen-kinetics mode, but it still remains below both Stage 9 and persistence
on this particular GTV-derived observation task.

Therefore the current project solver and grid/refinement calibration are not
the only bottleneck.

## What this result does not establish

This is **not** a faithful reproduction of the full published HGG TumorTwin
workflow.

Version 1 deliberately used the project's existing GTV-derived latent density
for an apples-to-apples comparison and recorded:

`adc_cellularity_used = false`

Two important fidelity gaps remain:

1. the upstream HGG workflow uses ADC-derived cellularity rather than only a
   GTV-derived density field;
2. the upstream examples calibrate on tumor-centric cropped regions, whereas
   reference benchmark v1 optimized the full prepared brain grid.

The full-brain least-squares objective contains many background-zero voxels and
can therefore change the inverse problem substantially.

It would be premature to conclude from v1 that the published HGG approach
itself is inferior on CFB.

## Failure cases

The LM reference retained five predefined catastrophic failures
(`delta_vs_persistence < -0.10`). The largest deficits included patients:

- 205: delta approximately `-0.4154`;
- 108: delta approximately `-0.3841`;
- 112: delta approximately `-0.2373`;
- 120: delta approximately `-0.1601`;
- 70: delta approximately `-0.1236`.

These overlap important regression/response failure modes already identified
during Stage 9.

## mpMRI availability consequence

The local filename audit found:

- 26 patient directories;
- 26 longitudinal T1Gd cases;
- 25 longitudinal FLAIR cases;
- 9 longitudinal ADC cases;
- 0 longitudinal DWI cases;
- 25 longitudinal T1Gd + FLAIR cases;
- 9 longitudinal T1Gd + ADC cases.

For the next calibration diagnostic, t2 ADC is not required. Only pre-target
t0/t1 ADC may be used to construct the calibration/assimilation state.

Within the already exposed Stage 9 cohort, the locally available t0+t1 ADC
subset is:

`25, 45, 65, 70, 76, 99, 112, 120, 214`

This allows a paired ADC-vs-GTV diagnostic without opening any new patients.

## Decision

Do not start Stage 10 yet.

First perform **Reference Fidelity v2** on the same exposed development data:

1. repeat upstream LM with a tumor-centric ROI crop on all 24 patients;
2. on the nine patients with t0+t1 ADC, repeat the same ROI-cropped LM using
   the pinned TumorTwin ADC-to-cellularity transform;
3. compare ADC and GTV modes on exactly the same nine patients;
4. keep reserve and untouched holdout sealed;
5. do not use t2 ADC and do not invent a FLAIR intensity threshold.

Only after this diagnostic should the project decide whether the next change
belongs in calibration/observation or in the Stage 10 treatment-state model.
