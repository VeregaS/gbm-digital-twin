import matplotlib.pyplot as plt
import numpy as np

from gbm_twin.data.models import PatientTimepointStudy


def largest_gtv_slice(gtv: np.ndarray) -> int:
    if gtv.ndim != 3:
        raise ValueError(f"Expected 3D GTV, got shape {gtv.shape}")

    areas = np.count_nonzero(gtv > 0, axis=(0, 1))

    if areas.max() == 0:
        raise ValueError("GTV mask is empty")

    return int(np.argmax(areas))


def plot_t1gd_gtv_overlay(
    study: PatientTimepointStudy,
) -> None:
    slice_index = largest_gtv_slice(study.gtv.data)

    image = study.t1gd.data[:, :, slice_index]
    gtv = study.gtv.data[:, :, slice_index] > 0

    fig, ax = plt.subplots(figsize=(8, 8))

    ax.imshow(
        np.rot90(image),
        cmap="gray",
    )

    ax.contour(
        np.rot90(gtv),
        levels=[0.5],
        linewidths=1.5,
    )

    ax.set_title(
        f"Patient {study.patient_id} — "
        f"{study.timepoint.name} — slice {slice_index}"
    )

    ax.axis("off")

    plt.tight_layout()
    plt.show()