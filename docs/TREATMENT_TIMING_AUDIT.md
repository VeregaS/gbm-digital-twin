# Treatment Timing Audit

Status: development diagnostic.

This audit exists to answer one narrow question before changing the tumour
dynamics model:

> At the observed `t1` state, is reconstructed fractionated radiotherapy still
> active, or has the reconstructed RT course already finished?

The distinction matters because the current V2/V2-accuracy-v1 forecast passes
the reconstructed fraction schedule into the solver. If all reconstructed
fractions occur before `t1`, then the `t1 -> t2` forecast receives no further
fraction events. A later observed tumour regression therefore cannot be
explained by future RT fractions in the current model.

The audit uses only:

- patient ID;
- `t1` day from longitudinal MRI metadata;
- RT start day;
- total RT dose;
- number of RT fractions;
- the existing deterministic weekday-like schedule reconstruction.

It does **not** load or use:

- `t2` MRI;
- `t2` GTV;
- `t2` tumour volume;
- held-out forecast metrics.

Run:

```powershell
python scripts\twin\audit_treatment_timing.py `
  --repo-root . `
  --experiment-config configs\experiments\mini_cohort_accuracy_v1.yaml
```

Default output:

```text
results/cohort/treatment-timing-audit/
  treatment_timing_audit.json
  treatment_timing_audit.sha256
  treatment_timing_audit.csv
```

Per-patient fields:

```text
patient_id
t1_day
treatment_reconstructable
rt_start_day
total_dose_gy
fractions_number
last_fraction_day
rt_completed_by_t1
fractions_after_t1
days_from_last_fraction_to_t1
```

`fractions_after_t1` counts reconstructed fractions strictly after the `t1`
day. `days_from_last_fraction_to_t1` is positive when `t1` occurs after the
last reconstructed fraction and negative when `t1` occurs before RT
completion.

This diagnostic does not itself justify a delayed treatment-response model.
It only establishes the temporal relationship between `t1` and reconstructed
RT. Any post-RT response model introduced after the held-out V2 results were
revealed is a new development model and must not be represented as the frozen
V2 protocol.
