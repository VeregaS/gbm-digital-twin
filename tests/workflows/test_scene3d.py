import numpy as np
import pytest

from gbm_twin.workflows.scene3d import (
    surface_mesh_from_mask,
    surface_mesh_from_scalar_field,
)


def test_surface_mesh_from_mask() -> None:
    mask = np.zeros(
        (16, 16, 16),
        dtype=bool,
    )

    mask[
        4:12,
        5:11,
        6:10,
    ] = True

    mesh = surface_mesh_from_mask(
        mask,
        spacing=(
            2.0,
            2.0,
            2.0,
        ),
        name="gtv",
    )

    assert mesh.name == "gtv"
    assert mesh.vertex_count > 0
    assert mesh.triangle_count > 0

    assert (
        mesh.vertices.shape[1]
        == 3
    )

    assert (
        mesh.triangles.shape[1]
        == 3
    )

    assert (
        mesh.vertices.dtype
        == np.float32
    )

    assert (
        mesh.triangles.dtype
        == np.uint32
    )


def test_smoothed_surface_mesh() -> None:
    mask = np.zeros(
        (20, 20, 20),
        dtype=bool,
    )

    mask[
        4:16,
        4:16,
        4:16,
    ] = True

    mesh = surface_mesh_from_mask(
        mask,
        spacing=(
            2.0,
            2.0,
            2.0,
        ),
        name="brain",
        smoothing_sigma_voxels=1.0,
    )

    assert mesh.vertex_count > 0
    assert mesh.triangle_count > 0

    assert np.all(
        np.isfinite(
            mesh.vertices
        )
    )


def test_scalar_field_surface() -> None:
    coordinates = np.indices(
        (24, 24, 24),
        dtype=np.float32,
    )

    x = coordinates[0] - 12.0
    y = coordinates[1] - 12.0
    z = coordinates[2] - 12.0

    radius = np.sqrt(
        x * x
        + y * y
        + z * z
    )

    field = np.exp(
        -radius / 4.0
    ).astype(
        np.float32
    )

    mesh = (
        surface_mesh_from_scalar_field(
            field,
            level=0.2,
            spacing=(
                2.0,
                2.0,
                2.0,
            ),
            name="latent",
        )
    )

    assert mesh.vertex_count > 0
    assert mesh.triangle_count > 0


def test_scalar_field_level_outside_range_returns_empty() -> None:
    field = np.zeros(
        (10, 10, 10),
        dtype=np.float32,
    )

    mesh = (
        surface_mesh_from_scalar_field(
            field,
            level=0.5,
            spacing=(
                2.0,
                2.0,
                2.0,
            ),
            name="latent",
        )
    )

    assert mesh.vertex_count == 0
    assert mesh.triangle_count == 0


def test_surface_mesh_empty_mask() -> None:
    mask = np.zeros(
        (8, 8, 8),
        dtype=bool,
    )

    mesh = surface_mesh_from_mask(
        mask,
        spacing=(
            2.0,
            2.0,
            2.0,
        ),
        name="gtv",
    )

    assert mesh.vertex_count == 0
    assert mesh.triangle_count == 0


def test_surface_mesh_rejects_2d() -> None:
    mask = np.zeros(
        (8, 8),
        dtype=bool,
    )

    with pytest.raises(
        ValueError,
        match="Expected 3D mask",
    ):
        surface_mesh_from_mask(
            mask,
            spacing=(
                2.0,
                2.0,
                2.0,
            ),
            name="gtv",
        )


def test_surface_mesh_rejects_negative_smoothing() -> None:
    mask = np.ones(
        (8, 8, 8),
        dtype=bool,
    )

    with pytest.raises(
        ValueError,
        match="must be non-negative",
    ):
        surface_mesh_from_mask(
            mask,
            spacing=(
                2.0,
                2.0,
                2.0,
            ),
            name="brain",
            smoothing_sigma_voxels=-1.0,
        )