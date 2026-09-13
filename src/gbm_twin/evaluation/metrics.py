import numpy as np

from gbm_twin.data.nifti import NiftiVolume


def mask_volume_cm3(
    volume: NiftiVolume,
    *,
    threshold: float = 0.5,
) -> float:
    mask = volume.data > threshold

    voxel_count = int(np.count_nonzero(mask))

    voxel_volume_mm3 = float(np.prod(volume.spacing))

    volume_mm3 = voxel_count * voxel_volume_mm3

    return volume_mm3 / 1000.0

def dice_score(
    first: np.ndarray,
    second: np.ndarray,
) -> float:
    first = first.astype(bool)
    second = second.astype(bool)

    if first.shape != second.shape:
        raise ValueError(
            f"Shape mismatch: {first.shape} vs {second.shape}"
        )

    intersection = np.count_nonzero(first & second)
    total = np.count_nonzero(first) + np.count_nonzero(second)

    if total == 0:
        return 1.0

    return 2.0 * intersection / total

def relative_volume_error(
    predicted: np.ndarray,
    observed: np.ndarray,
) -> float:
    predicted = predicted.astype(bool)
    observed = observed.astype(bool)

    if predicted.shape != observed.shape:
        raise ValueError(
            f"Shape mismatch: {predicted.shape} vs {observed.shape}"
        )

    observed_count = np.count_nonzero(observed)

    if observed_count == 0:
        raise ValueError("Observed mask is empty")

    predicted_count = np.count_nonzero(predicted)

    return abs(predicted_count - observed_count) / observed_count