from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from fastapi import Request


DEFAULT_CFB_ROOT = Path(
    r"D:\Datasets\CFB-GBM"
)


@dataclass(frozen=True)
class ApiSettings:
    dataset_root: Path

    metadata_root: Path
    patients_root: Path

    atlas_root: Path | None = None

    @classmethod
    def from_environment(
        cls,
    ) -> ApiSettings:
        dataset_root = Path(
            os.environ.get(
                "GBM_TWIN_CFB_ROOT",
                str(
                    DEFAULT_CFB_ROOT
                ),
            )
        )

        default_metadata_root = (
            dataset_root
            / "metadata"
        )

        if not (
            default_metadata_root
            .is_dir()
        ):
            default_metadata_root = (
                dataset_root
            )

        metadata_root = Path(
            os.environ.get(
                "GBM_TWIN_CFB_METADATA_ROOT",
                str(
                    default_metadata_root
                ),
            )
        )

        patients_root = Path(
            os.environ.get(
                "GBM_TWIN_CFB_PATIENTS_ROOT",
                str(
                    dataset_root
                    / "patients"
                ),
            )
        )

        atlas_root_text = (
            os.environ.get(
                "GBM_TWIN_ATLAS_ROOT"
            )
        )

        atlas_root = (
            None
            if not atlas_root_text
            else Path(
                atlas_root_text
            )
        )

        return cls(
            dataset_root=dataset_root,
            metadata_root=metadata_root,
            patients_root=patients_root,
            atlas_root=atlas_root,
        )


def get_api_settings(
    request: Request,
) -> ApiSettings:
    settings = (
        request.app.state.settings
    )

    if not isinstance(
        settings,
        ApiSettings,
    ):
        raise RuntimeError(
            "API settings are "
            "not initialized"
        )

    return settings