from pathlib import Path

from gbm_twin.calibration.grid_search import grid_search
from gbm_twin.data.models import Timepoint
from gbm_twin.data.nifti import same_geometry
from gbm_twin.data.patient_loader import load_patient_timepoint
from gbm_twin.models.reaction_diffusion import (
    build_computational_domain,
    initial_condition_from_gtv,
)
from gbm_twin.preprocessing.resampling import resample_volume


def main() -> None:
    root = Path(r"D:\Datasets\CFB-GBM\patients")

    # t0
    t0 = load_patient_timepoint(
        root,
        42,
        Timepoint("t0", 0),
    )

    t0_gtv = resample_volume(
        t0.gtv,
        (2.0, 2.0, 2.0),
        is_mask=True,
    )

    t0_brain = resample_volume(
        t0.brain_mask,
        (2.0, 2.0, 2.0),
        is_mask=True,
    )

    domain = build_computational_domain(
        t0_brain.data,
        t0_gtv.data,
    )

    initial = initial_condition_from_gtv(
        t0_gtv.data,
        domain,
    )

    # t1
    t1 = load_patient_timepoint(
        root,
        42,
        Timepoint("t1", 77),
    )

    t1_gtv = resample_volume(
        t1.gtv,
        (2.0, 2.0, 2.0),
        is_mask=True,
    )

    if not same_geometry(t0_gtv, t1_gtv):
        raise ValueError(
            "t0 and t1 computational grids do not match"
        )

    observed_gtv = t1_gtv.data > 0.5

    # Coarse calibration grid
    results = grid_search(
        initial,
        observed_gtv,
        domain,
        spacing=t0_gtv.spacing,
        duration_days=77.0,
        dt=2.0,
        diffusion_values=[
            0.0025,
            0.0050,
            0.0075,
            0.0100,
            0.0125,
        ],
        proliferation_values=[
            0.045,
            0.050,
            0.055,
        ],
        threshold=0.5,
    )

    print()
    print("Calibration results:")
    print("--------------------")

    for item in results:
        print(
            f"D={item.diffusion:.3f} "
            f"rho={item.proliferation:.3f} "
            f"Dice={item.dice:.4f}"
        )

    best = results[0]

    print()
    print("Best parameters:")
    print(
        f"D={best.diffusion:.3f}, "
        f"rho={best.proliferation:.3f}, "
        f"Dice={best.dice:.4f}"
    )


if __name__ == "__main__":
    main()