# Sealed Stage 10 reserve data preparation

`run_stage10_reserve_validation.ps1` now prepares the reserve inputs automatically
after creating or loading the sealed plan, and before validation preflight.
An existing plan is verified and reused; it is never regenerated because files
are missing. The reported cohort remains
`15,47,57,71,73,91,139,140,142,144,161,194,201,234,241,254`.
The authoritative IDs come from the sealed plan, not a second CLI patient list.

```powershell
git pull
powershell -ExecutionPolicy Bypass -File scripts\twin\run_stage10_reserve_validation.ps1 `
  -SourceDataRoot D:\Datasets\CFB-GBM\data
```

The source must be the **extracted official CFB-GBM NIfTI release** containing
`<id>/<t0|t1|t2>/<id>_<timepoint>_{t1gd,gtv,brain_mask}.nii.gz`, plus RTDOSE
when required by the selected Stage 8 model. This follows the existing
[Stage 8 ingestion workflow](STAGE8_DATA_MATERIALIZATION.md); it does not recreate
the authors' masks or registrations from raw DICOM. The destination comes from
the experiment configuration (`patients_root`). Source resolution is explicit
`--source-data-root`, then `GBM_TWIN_CFB_SOURCE_DATA_ROOT`, then
`GBM_TWIN_CFB_ROOT/data`, then the sibling `data/` next to `patients/`.

To inspect preparation without running the accuracy experiment:

```powershell
python scripts\twin\materialize_stage10_reserve.py `
  --validation-plan-root results\cohort\stage10-reserve-validation-plan-v1 `
  --source-data-root D:\Datasets\CFB-GBM\data --dry-run
```

Remove `--dry-run` to prepare files only. `--mode auto` tries hardlinks and falls
back to copy; `copy` and `hardlink` are also available. Treat linked prepared
inputs as read-only, because hardlinks share storage with the official source.
The runner exposes `-MaterializationMode` for the same choice.

Before any patient-file access, preparation checks the plan checksum, audit,
Stage 8/10 selections, frozen model, protocol and experiment/config provenance.
It checks the prespecified metadata-only selection against the sealed IDs and
remaining reserve/holdout partitions, without modifying the plan. It then
checks every source and every existing destination before writing. Missing or
empty sources, ambiguous RTDOSE and conflicting destination bytes cause an
error; patients are never dropped or substituted. Successful existing files
are reused, making interrupted runs resumable. Transfers use temporary files
and atomic replacement, following the existing Stage 8 materializer.

Materialization transfers opaque NIfTI bytes (and may compare byte checksums);
it does not decode, render, measure, or segment MRI. It never visits unselected
reserve or holdout patient directories. The first interpretation of each
reserve patient's t2 remains in `validate_stage10_model.py`, after that patient's
D/rho have been frozen from t0/t1. Scientific criteria, model parameters,
bootstrap settings and validation outcome rules are unchanged.

If `data/` is absent, preparation stops before creating patient files and lists
the expected missing paths. Extract the official NIfTI package and rerun with
its data root. The workflow does not download a dataset or launch the expensive
validation experiment during development checks.
