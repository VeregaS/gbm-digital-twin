from dataclasses import dataclass

import numpy as np

Slice3D = tuple[
    slice,
    slice,
    slice,
]


@dataclass(frozen=True)
class DomainCrop:
    original_shape: tuple[int, int, int]
    slices: Slice3D

    @classmethod
    def from_mask(
        cls,
        mask: np.ndarray,
    ) -> "DomainCrop":
        if mask.ndim != 3:
            raise ValueError(
                f"Expected 3D mask, got shape {mask.shape}"
            )

        domain = np.asarray(
            mask,
            dtype=bool,
        )

        coordinates = np.nonzero(
            domain
        )

        if coordinates[0].size == 0:
            raise ValueError(
                "Domain mask is empty"
            )

        slices: Slice3D = (
            slice(
                int(coordinates[0].min()),
                int(coordinates[0].max()) + 1,
            ),
            slice(
                int(coordinates[1].min()),
                int(coordinates[1].max()) + 1,
            ),
            slice(
                int(coordinates[2].min()),
                int(coordinates[2].max()) + 1,
            ),
        )

        return cls(
            original_shape=domain.shape,
            slices=slices,
        )

    @property
    def cropped_shape(
        self,
    ) -> tuple[int, int, int]:
        shape: list[int] = []

        for axis_slice in self.slices:
            if (
                axis_slice.start is None
                or axis_slice.stop is None
            ):
                raise RuntimeError(
                    "Crop slices must have explicit bounds"
                )

            shape.append(
                axis_slice.stop
                - axis_slice.start
            )

        return (
            shape[0],
            shape[1],
            shape[2],
        )

    def crop(
        self,
        array: np.ndarray,
    ) -> np.ndarray:
        if array.shape != self.original_shape:
            raise ValueError(
                f"Array shape {array.shape} does not match "
                f"original shape {self.original_shape}"
            )

        return array[
            self.slices
        ]

    def restore(
        self,
        cropped: np.ndarray,
    ) -> np.ndarray:
        if cropped.shape != self.cropped_shape:
            raise ValueError(
                f"Cropped shape {cropped.shape} does not match "
                f"expected shape {self.cropped_shape}"
            )

        restored = np.zeros(
            self.original_shape,
            dtype=cropped.dtype,
        )

        restored[
            self.slices
        ] = cropped

        return restored