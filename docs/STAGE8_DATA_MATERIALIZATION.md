# Stage 8 CFB-GBM data materialization

## Purpose

Stage 8 separates two different concepts:

1. **metadata eligibility** — the official CFB-GBM metadata says a patient has
   the inputs required by the scientific protocol;
2. **local materialization** — the corresponding NIfTI files are physically
   present under the local `patients/` root used by the experiment.

The sealed Stage 8 data audit defines the scientific split. Missing local files
must never be used as a reason to silently remove or replace a patient after
model selection.

## Official source layout

The CFB-GBM NIfTI release is already preprocessed by the dataset authors and
uses the layout:

```text
data/
└── <patient_id>/
    ├── t0/
    │   ├── <id>_t0_t1gd.nii.gz
    │   ├── <id>_t0_gtv.nii.gz
    │   └── <id>_t0_brain_mask.nii.gz
    ├── t1/
    │   └── ...
    └── t2/
        └── ...
```

Stage 8 therefore does not regenerate T1Gd, GTV, or brain masks for cohort
materialization. It reuses the official NIfTI release.

## Internal-validation materialization

Use:

```powershell
python scripts\twin\materialize_stage8_cohort.py `
  --repo-root . `
  --data-audit-root results\cohort\stage8-data-audit-v1 `
  --selection-root results\cohort\stage8-model-selection-v1 `
  --source-data-root D:\Datasets\CFB-GBM\data `
  --mode auto
```

The workflow:

- loads the sealed Stage 8 audit;
- loads the sealed selected model;
- verifies that both artifacts refer to the same audit SHA;
- selects only the predeclared internal-validation patients;
- verifies all required source files before writing any destination file;
- never substitutes an untouched-holdout patient;
- uses hardlinks when possible and copies only when hardlink creation fails;
- verifies already materialized files against their official source;
- is safe to rerun.

A dry run is available:

```powershell
python scripts\twin\materialize_stage8_cohort.py `
  --repo-root . `
  --data-audit-root results\cohort\stage8-data-audit-v1 `
  --selection-root results\cohort\stage8-model-selection-v1 `
  --source-data-root D:\Datasets\CFB-GBM\data `
  --dry-run
```

## Leakage boundary

Materialization may copy or hardlink the t2 NIfTI bytes, but it does not load,
measure, render, segment, or otherwise inspect t2 image content.

The first workflow allowed to interpret internal-validation t2 is
`validate_stage8_model.py`, after the selected model has already been sealed.

The untouched holdout remains outside this materialization workflow and must
not be opened during internal validation.

## Missing official source archive

If the official CFB-GBM `data/` directory is not present locally, the NIfTI
release must be downloaded from the TCIA CFB-GBM collection before
materialization. The project does not attempt to re-create the official masks
or registrations from raw imaging as a substitute.
