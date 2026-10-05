from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from gbm_twin.workflows.provenance import (
    sha256_file,
)
from gbm_twin.workflows.stage8_data_audit import (
    load_sealed_stage8_data_audit,
)
from gbm_twin.workflows.stage8_selection_artifact import (
    load_selected_stage8_model,
)
from gbm_twin.workflows.stage10_selection_artifact import (
    load_selected_stage10_model,
)
from gbm_twin.workflows.stage10_validation_protocol import (
    load_stage10_validation_config,
    verify_frozen_stage10_model,
)

STAGE10_VALIDATION_PLAN_SCHEMA_VERSION = 1
STAGE10_VALIDATION_PLAN_KIND = (
    "stage10_reserve_validation_plan"
)


@dataclass(frozen=True)
class Stage10ValidationPlan:
    directory: Path
    patient_ids: tuple[int, ...]
    remaining_reserve_patient_ids: tuple[int, ...]
    untouched_holdout_patient_ids: tuple[int, ...]
    stage10_selection_sha256: str
    stage8_data_audit_sha256: str
    frozen_model_config_sha256: str
    validation_config_sha256: str
    seed: int


def _patient_rows(
    manifest: dict[str, object],
) -> dict[
    int,
    dict[str, object],
]:
    raw = manifest.get(
        "patients"
    )

    if not isinstance(
        raw,
        list,
    ):
        raise ValueError(
            "Stage 8 audit patient rows are missing"
        )

    rows: dict[
        int,
        dict[str, object],
    ] = {}

    for item in raw:
        if not isinstance(
            item,
            dict,
        ):
            raise ValueError(
                "Stage 8 audit patient row must be a mapping"
            )

        row = cast(
            dict[str, object],
            item,
        )

        patient_id = row.get(
            "patient_id"
        )

        if type(
            patient_id
        ) is not int:
            raise ValueError(
                "Stage 8 audit patient_id must be integer"
            )

        rows[
            cast(
                int,
                patient_id,
            )
        ] = row

    return rows


def _stratum(
    row: dict[str, object],
) -> str:
    value = row.get(
        "split_stratum"
    )

    if (
        not isinstance(
            value,
            str,
        )
        or not value
    ):
        raise ValueError(
            "Stage 8 audit split_stratum is missing"
        )

    return value


def _rank(
    seed: int,
    stratum: str,
    patient_id: int,
) -> str:
    payload = (
        "stage10-reserve-validation-v1:"
        f"{seed}:{stratum}:{patient_id}"
    )

    return hashlib.sha256(
        payload.encode(
            "ascii"
        )
    ).hexdigest()


def select_stage10_reserve_patient_ids(
    *,
    audit_manifest: dict[str, object],
    reserve_patient_ids: tuple[int, ...],
    untouched_holdout_patient_ids: tuple[int, ...],
    count: int,
    seed: int,
) -> tuple[int, ...]:
    if count < 1:
        raise ValueError(
            "Stage 10 validation patient count must be positive"
        )

    if count > len(
        reserve_patient_ids
    ):
        raise ValueError(
            "Stage 10 validation patient count exceeds reserve cohort"
        )

    rows = _patient_rows(
        audit_manifest
    )

    groups: dict[
        str,
        list[int],
    ] = {}

    holdout = set(
        untouched_holdout_patient_ids
    )

    for patient_id in (
        reserve_patient_ids
    ):
        if patient_id in holdout:
            raise ValueError(
                f"Reserve patient {patient_id} is in untouched holdout"
            )

        row = rows.get(
            patient_id
        )

        if row is None:
            raise ValueError(
                f"Reserve patient {patient_id} is absent from data audit"
            )

        if (
            row.get(
                "split"
            )
            == "untouched-holdout"
        ):
            raise ValueError(
                f"Reserve patient {patient_id} is in untouched holdout"
            )

        groups.setdefault(
            _stratum(
                row
            ),
            [],
        ).append(
            patient_id
        )

    ordered: dict[
        str,
        list[int],
    ] = {
        stratum: sorted(
            patient_ids,
            key=lambda patient_id: (
                _rank(
                    seed,
                    stratum,
                    patient_id,
                )
            ),
        )
        for (
            stratum,
            patient_ids,
        ) in sorted(
            groups.items()
        )
    }

    selected: dict[
        str,
        list[int],
    ] = {
        stratum: []
        for stratum in ordered
    }

    if (
        count
        >= len(
            ordered
        )
    ):
        for (
            stratum,
            patient_ids,
        ) in ordered.items():
            selected[
                stratum
            ].append(
                patient_ids[
                    0
                ]
            )

    while (
        sum(
            len(
                values
            )
            for values in (
                selected.values()
            )
        )
        < count
    ):
        eligible = [
            stratum
            for (
                stratum,
                patient_ids,
            ) in ordered.items()
            if (
                len(
                    selected[
                        stratum
                    ]
                )
                < len(
                    patient_ids
                )
            )
        ]

        if not eligible:
            break

        stratum = min(
            eligible,
            key=lambda name: (
                len(
                    selected[
                        name
                    ]
                )
                / len(
                    ordered[
                        name
                    ]
                ),
                name,
            ),
        )

        selected[
            stratum
        ].append(
            ordered[
                stratum
            ][
                len(
                    selected[
                        stratum
                    ]
                )
            ]
        )

    result = tuple(
        sorted(
            patient_id
            for values in (
                selected.values()
            )
            for patient_id in values
        )
    )

    if len(
        result
    ) != count:
        raise RuntimeError(
            "Failed to construct Stage 10 validation cohort"
        )

    return result


def verify_stage10_validation_cohort(
    plan: Stage10ValidationPlan,
    *,
    audit_manifest: dict[str, object],
    reserve_patient_ids: tuple[int, ...],
    untouched_holdout_patient_ids: tuple[int, ...],
    count: int,
    seed: int,
) -> None:
    """Check membership and the entire selection rule before accessing images."""
    expected = select_stage10_reserve_patient_ids(
        audit_manifest=audit_manifest,
        reserve_patient_ids=reserve_patient_ids,
        untouched_holdout_patient_ids=untouched_holdout_patient_ids,
        count=count,
        seed=seed,
    )
    if (
        plan.patient_ids != expected
        or plan.seed != seed
        or plan.remaining_reserve_patient_ids
        != tuple(sorted(set(reserve_patient_ids) - set(expected)))
        or plan.untouched_holdout_patient_ids != untouched_holdout_patient_ids
    ):
        raise ValueError("Stage 10 sealed cohort differs from the prespecified reserve plan")


def _required_paths(
    patient_ids: tuple[int, ...],
    *,
    require_spatial_rtdose: bool,
) -> tuple[str, ...]:
    paths: list[str] = []

    for patient_id in (
        patient_ids
    ):
        for timepoint in (
            "t0",
            "t1",
            "t2",
        ):
            prefix = (
                f"{patient_id}_{timepoint}"
            )

            for suffix in (
                "t1gd",
                "gtv",
                "brain_mask",
            ):
                paths.append(
                    f"{patient_id}/{timepoint}/"
                    f"{prefix}_{suffix}.nii.gz"
                )

        if require_spatial_rtdose:
            paths.append(
                f"{patient_id}/**/*rtdose*.nii.gz"
            )

    return tuple(
        paths
    )


def create_stage10_validation_plan(
    *,
    data_audit_root: Path,
    stage8_selection_root: Path,
    stage10_selection_root: Path,
    frozen_model_config_path: Path,
    validation_config_path: Path,
    output_dir: Path,
) -> Stage10ValidationPlan:
    destination = (
        output_dir.resolve()
    )

    if destination.exists():
        raise FileExistsError(
            "Stage 10 validation-plan destination exists: "
            f"{destination}"
        )

    audit = (
        load_sealed_stage8_data_audit(
            data_audit_root
        )
    )

    selected_stage8 = (
        load_selected_stage8_model(
            stage8_selection_root
        )
    )

    selected = (
        load_selected_stage10_model(
            stage10_selection_root
        )
    )

    frozen = (
        verify_frozen_stage10_model(
            selected=selected,
            config_path=(
                frozen_model_config_path
            ),
        )
    )

    validation = (
        load_stage10_validation_config(
            validation_config_path
        )
    )

    audit_sha = (
        sha256_file(
            data_audit_root.resolve()
            / "stage8_data_audit.json"
        )
    )

    if (
        selected
        .stage8_data_audit_sha256
        != audit_sha
    ):
        raise ValueError(
            "Stage 10 selection does not match the sealed data audit"
        )

    stage8_selection_sha = (
        sha256_file(
            stage8_selection_root.resolve()
            / "stage8_model_selection.json"
        )
    )

    if (
        selected_stage8
        .stage8_data_audit_sha256
        != audit_sha
    ):
        raise ValueError(
            "Stage 8 selection does not match the sealed data audit"
        )

    if (
        selected
        .stage8_model_selection_sha256
        != stage8_selection_sha
    ):
        raise ValueError(
            "Stage 10 selection does not match Stage 8 selection"
        )

    patient_ids = (
        select_stage10_reserve_patient_ids(
            audit_manifest=(
                audit.manifest
            ),
            reserve_patient_ids=(
                selected
                .reserve_patient_ids
            ),
            untouched_holdout_patient_ids=(
                selected
                .untouched_holdout_patient_ids
            ),
            count=(
                validation
                .patient_count
            ),
            seed=(
                validation.seed
            ),
        )
    )

    remaining = tuple(
        sorted(
            set(
                selected
                .reserve_patient_ids
            )
            - set(
                patient_ids
            )
        )
    )

    frozen_sha = (
        sha256_file(
            frozen_model_config_path.resolve()
        )
    )

    validation_sha = (
        sha256_file(
            validation_config_path.resolve()
        )
    )

    payload: dict[
        str,
        object,
    ] = {
        "schema_version": (
            STAGE10_VALIDATION_PLAN_SCHEMA_VERSION
        ),
        "kind": (
            STAGE10_VALIDATION_PLAN_KIND
        ),
        "sealed": True,
        "source": {
            "stage8_data_audit_sha256": (
                audit_sha
            ),
            "stage8_model_selection_sha256": (
                stage8_selection_sha
            ),
            "stage10_selection_sha256": (
                selected
                .source_manifest_sha256
            ),
            "frozen_model_config_sha256": (
                frozen_sha
            ),
            "validation_config_sha256": (
                validation_sha
            ),
        },
        "frozen_model": {
            "model_id": (
                frozen.model_id
            ),
            "kind": (
                frozen
                .candidate_kind
            ),
            "visible_damage_half_life_days": (
                frozen
                .visible_damage_half_life_days
            ),
        },
        "selection_rule": {
            "method": (
                validation
                .selection_method
            ),
            "seed": (
                validation.seed
            ),
            "requested_patient_count": (
                validation
                .patient_count
            ),
            "uses_outcomes": False,
            "loads_t2_image_content": False,
        },
        "patient_ids": (
            list(
                patient_ids
            )
        ),
        "remaining_reserve_patient_ids": (
            list(
                remaining
            )
        ),
        "untouched_holdout_patient_ids": (
            list(
                selected
                .untouched_holdout_patient_ids
            )
        ),
        "leakage_control": {
            "reserve_t2_loaded": False,
            "untouched_holdout_t2_loaded": False,
            "selection_uses_metadata_only": True,
            "global_model_parameters_changed": False,
        },
    }

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = Path(
        tempfile.mkdtemp(
            dir=(
                destination.parent
            ),
            prefix=(
                f".{destination.name}-"
            ),
        )
    )

    try:
        manifest_path = (
            temporary
            / "stage10_validation_plan.json"
        )

        manifest_path.write_text(
            json.dumps(
                payload,
                indent=2,
                sort_keys=True,
                allow_nan=False,
            )
            + "\n",
            encoding="utf-8",
        )

        (
            temporary
            / "stage10_validation_plan.sha256"
        ).write_text(
            (
                sha256_file(
                    manifest_path
                )
                + "  stage10_validation_plan.json\n"
            ),
            encoding="ascii",
        )

        (
            temporary
            / "stage10_validation_patient_ids.txt"
        ).write_text(
            (
                "\n".join(
                    str(
                        value
                    )
                    for value in (
                        patient_ids
                    )
                )
                + "\n"
            ),
            encoding="ascii",
        )

        (
            temporary
            / "stage10_validation_required_paths.txt"
        ).write_text(
            (
                "\n".join(
                    _required_paths(
                        patient_ids,
                        require_spatial_rtdose=(
                            selected_stage8
                            .candidate
                            .use_spatial_rtdose
                        ),
                    )
                )
                + "\n"
            ),
            encoding="utf-8",
        )

        temporary.rename(
            destination
        )

    except BaseException:
        shutil.rmtree(
            temporary,
            ignore_errors=True,
        )
        raise

    return load_stage10_validation_plan(
        destination
    )


def _mapping(
    mapping: dict[str, object],
    key: str,
) -> dict[str, object]:
    value = mapping.get(
        key
    )

    if not isinstance(
        value,
        dict,
    ):
        raise ValueError(
            f"Stage 10 plan field {key!r} must be a mapping"
        )

    return cast(
        dict[str, object],
        value,
    )


def _string(
    mapping: dict[str, object],
    key: str,
) -> str:
    value = mapping.get(
        key
    )

    if (
        not isinstance(
            value,
            str,
        )
        or not value
    ):
        raise ValueError(
            f"Stage 10 plan field {key!r} must be string"
        )

    return value


def _int_tuple(
    mapping: dict[str, object],
    key: str,
) -> tuple[int, ...]:
    value = mapping.get(
        key
    )

    if not isinstance(
        value,
        list,
    ):
        raise ValueError(
            f"Stage 10 plan field {key!r} must be list"
        )

    result: list[int] = []

    for item in value:
        if type(
            item
        ) is not int:
            raise ValueError(
                f"Stage 10 plan field {key!r} must contain integers"
            )

        result.append(
            cast(
                int,
                item,
            )
        )

    return tuple(
        result
    )


def load_stage10_validation_plan(
    directory: Path,
) -> Stage10ValidationPlan:
    root = (
        directory.resolve()
    )

    manifest_path = (
        root
        / "stage10_validation_plan.json"
    )

    seal_path = (
        root
        / "stage10_validation_plan.sha256"
    )

    if (
        not manifest_path.is_file()
        or not seal_path.is_file()
    ):
        raise FileNotFoundError(
            "Stage 10 validation plan is incomplete"
        )

    tokens = seal_path.read_text(
        encoding="ascii"
    ).split()

    if (
        not tokens
        or tokens[0]
        != sha256_file(
            manifest_path
        )
    ):
        raise ValueError(
            "Stage 10 validation-plan checksum mismatch"
        )

    raw: object = json.loads(
        manifest_path.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(
        raw,
        dict,
    ):
        raise ValueError(
            "Stage 10 validation plan must be JSON object"
        )

    manifest = cast(
        dict[str, object],
        raw,
    )

    if (
        manifest.get(
            "schema_version"
        )
        != STAGE10_VALIDATION_PLAN_SCHEMA_VERSION
    ):
        raise ValueError(
            "Unsupported Stage 10 validation-plan schema"
        )

    if (
        manifest.get(
            "kind"
        )
        != STAGE10_VALIDATION_PLAN_KIND
    ):
        raise ValueError(
            "Artifact is not a Stage 10 validation plan"
        )

    if (
        manifest.get(
            "sealed"
        )
        is not True
    ):
        raise ValueError(
            "Stage 10 validation plan is not sealed"
        )

    leakage = _mapping(
        manifest,
        "leakage_control",
    )

    required_flags = {
        "reserve_t2_loaded": False,
        "untouched_holdout_t2_loaded": False,
        "selection_uses_metadata_only": True,
        "global_model_parameters_changed": False,
    }

    for (
        key,
        expected,
    ) in required_flags.items():
        if (
            leakage.get(
                key
            )
            is not expected
        ):
            raise ValueError(
                "Stage 10 validation-plan leakage contract is inconsistent: "
                f"{key}"
            )

    source = _mapping(
        manifest,
        "source",
    )

    rule = _mapping(
        manifest,
        "selection_rule",
    )

    seed = rule.get(
        "seed"
    )

    if type(
        seed
    ) is not int:
        raise ValueError(
            "Stage 10 validation-plan seed must be integer"
        )

    return Stage10ValidationPlan(
        directory=root,
        patient_ids=_int_tuple(
            manifest,
            "patient_ids",
        ),
        remaining_reserve_patient_ids=(
            _int_tuple(
                manifest,
                "remaining_reserve_patient_ids",
            )
        ),
        untouched_holdout_patient_ids=(
            _int_tuple(
                manifest,
                "untouched_holdout_patient_ids",
            )
        ),
        stage10_selection_sha256=(
            _string(
                source,
                "stage10_selection_sha256",
            )
        ),
        stage8_data_audit_sha256=(
            _string(
                source,
                "stage8_data_audit_sha256",
            )
        ),
        frozen_model_config_sha256=(
            _string(
                source,
                "frozen_model_config_sha256",
            )
        ),
        validation_config_sha256=(
            _string(
                source,
                "validation_config_sha256",
            )
        ),
        seed=cast(
            int,
            seed,
        ),
    )
