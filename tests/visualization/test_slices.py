import numpy as np

from gbm_twin.visualization.slices import largest_gtv_slice


def test_largest_gtv_slice() -> None:
    gtv = np.zeros((10, 10, 5), dtype=np.uint8)

    gtv[4:6, 4:6, 1] = 1
    gtv[2:8, 2:8, 3] = 1

    assert largest_gtv_slice(gtv) == 3