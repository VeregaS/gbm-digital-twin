from __future__ import annotations

from gbm_twin.workflows.reference_benchmark import (
    ReferenceBenchmarkRow,
    _summary,
)


def test_reference_summary_counts_failures_and_deltas() -> None:
    rows = [
        ReferenceBenchmarkRow(
            patient_id=1,
            engine="tumortwin-frozen",
            diffusion=0.01,
            proliferation=0.02,
            dice=0.8,
            persistence_dice=0.7,
            delta_vs_persistence=0.1,
            relative_volume_error=0.1,
            hd95_mm=2.0,
            centroid_distance_mm=1.0,
            stage9_dice=0.75,
            delta_vs_stage9=0.05,
        ),
        ReferenceBenchmarkRow(
            patient_id=2,
            engine="tumortwin-frozen",
            diffusion=0.02,
            proliferation=0.03,
            dice=0.4,
            persistence_dice=0.6,
            delta_vs_persistence=-0.2,
            relative_volume_error=0.4,
            hd95_mm=8.0,
            centroid_distance_mm=4.0,
            stage9_dice=0.5,
            delta_vs_stage9=-0.1,
        ),
    ]

    summary = _summary(rows)

    assert summary["patient_count"] == 2
    assert summary["catastrophic_failure_count"] == 1
    assert summary["better_than_persistence_count"] == 1
    assert summary["worse_than_persistence_count"] == 1
    assert summary["mean_dice"] == 0.6
