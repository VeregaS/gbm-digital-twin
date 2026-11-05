from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from gbm_twin.workflows.provenance import (
    sha256_file,
)


def _mapping(
    value: object,
    *,
    name: str,
) -> dict[str, object]:
    if not isinstance(
        value,
        dict,
    ):
        raise ValueError(
            f"{name} must be a mapping"
        )

    return cast(
        dict[str, object],
        value,
    )


def _number(
    mapping: dict[str, object],
    key: str,
) -> float:
    value = mapping.get(
        key
    )

    if (
        isinstance(
            value,
            bool,
        )
        or not isinstance(
            value,
            (int, float),
        )
    ):
        raise ValueError(
            f"{key} must be numeric"
        )

    return float(
        value
    )


def _integer(
    mapping: dict[str, object],
    key: str,
) -> int:
    value = mapping.get(
        key
    )

    if type(
        value
    ) is not int:
        raise ValueError(
            f"{key} must be integer"
        )

    return cast(
        int,
        value,
    )


def _optional_number(
    mapping: dict[str, object],
    key: str,
) -> float | None:
    value = mapping.get(
        key
    )

    if value is None:
        return None

    if (
        isinstance(
            value,
            bool,
        )
        or not isinstance(
            value,
            (int, float),
        )
    ):
        raise ValueError(
            f"{key} must be numeric or null"
        )

    return float(
        value
    )


def _fmt(
    value: float | None,
    *,
    signed: bool = False,
) -> str:
    if value is None:
        return "—"

    if signed:
        return f"{value:+.4f}"

    return f"{value:.4f}"


def render_stage10_validation_markdown(
    manifest: dict[str, object],
) -> str:
    if (
        manifest.get(
            "sealed"
        )
        is not True
    ):
        raise ValueError(
            "Stage 10 validation artifact must be sealed"
        )

    decision = str(
        manifest.get(
            "decision",
            "",
        )
    )

    if decision not in {
        "validation_passed",
        "validation_failed",
    }:
        raise ValueError(
            "Unsupported Stage 10 validation decision"
        )

    summary = _mapping(
        manifest.get(
            "summary"
        ),
        name="summary",
    )

    model = _mapping(
        manifest.get(
            "frozen_model"
        ),
        name="frozen_model",
    )

    leakage = _mapping(
        manifest.get(
            "leakage_control"
        ),
        name="leakage_control",
    )

    failed = manifest.get(
        "failed_guardrails"
    )

    if not isinstance(
        failed,
        list,
    ):
        raise ValueError(
            "failed_guardrails must be a list"
        )

    ci = summary.get(
        "bootstrap_mean_delta_ci95"
    )

    if (
        not isinstance(
            ci,
            list,
        )
        or len(
            ci
        )
        != 2
    ):
        raise ValueError(
            "bootstrap_mean_delta_ci95 must contain two values"
        )

    low = float(
        ci[
            0
        ]
    )

    high = float(
        ci[
            1
        ]
    )

    if decision == "validation_passed":
        conclusion = (
            "The frozen Stage 10 model passed every pre-specified "
            "reserve-validation guardrail."
        )

    else:
        conclusion = (
            "The frozen Stage 10 model did not pass every pre-specified "
            "reserve-validation guardrail. Do not tune on the revealed "
            "reserve outcomes."
        )

    lines = [
        "# Stage 10 — sealed reserve internal validation",
        "",
        f"Decision: `{decision}`",
        "",
        (
            "Frozen model: `"
            + str(
                model.get(
                    "model_id",
                    "",
                )
            )
            + "`"
        ),
        "",
        conclusion,
        "",
        "## Primary metrics",
        "",
        (
            "- patients: "
            + str(
                _integer(
                    summary,
                    "patient_count",
                )
            )
        ),
        (
            "- mean Twin Dice: "
            + _fmt(
                _number(
                    summary,
                    "mean_twin_dice",
                )
            )
        ),
        (
            "- mean persistence Dice: "
            + _fmt(
                _number(
                    summary,
                    "mean_persistence_dice",
                )
            )
        ),
        (
            "- mean delta vs persistence: "
            + _fmt(
                _number(
                    summary,
                    "mean_delta_vs_persistence",
                ),
                signed=True,
            )
        ),
        (
            "- median delta vs persistence: "
            + _fmt(
                _number(
                    summary,
                    "median_delta_vs_persistence",
                ),
                signed=True,
            )
        ),
        (
            "- bootstrap 95% CI for mean delta: ["
            + _fmt(
                low,
                signed=True,
            )
            + ", "
            + _fmt(
                high,
                signed=True,
            )
            + "]"
        ),
        (
            "- catastrophic failures: "
            + str(
                _integer(
                    summary,
                    "catastrophic_failure_count",
                )
            )
        ),
        (
            "- mean Twin RVE / persistence RVE: "
            + _fmt(
                _number(
                    summary,
                    "mean_twin_relative_volume_error",
                )
            )
            + " / "
            + _fmt(
                _number(
                    summary,
                    "mean_persistence_relative_volume_error",
                )
            )
        ),
        (
            "- mean Twin HD95 / persistence HD95: "
            + _fmt(
                _optional_number(
                    summary,
                    "mean_twin_hd95_mm",
                )
            )
            + " / "
            + _fmt(
                _optional_number(
                    summary,
                    "mean_persistence_hd95_mm",
                )
            )
            + " mm"
        ),
        "",
        "## Guardrails",
        "",
    ]

    if failed:
        lines.extend(
            [
                "Failed guardrails:",
                "",
                *[
                    f"- `{value}`"
                    for value in failed
                ],
            ]
        )
    else:
        lines.append(
            "All pre-specified guardrails passed."
        )

    lines.extend(
        [
            "",
            "## Leakage status",
            "",
            (
                "- validation patients revealed: "
                + str(
                    len(
                        cast(
                            list[object],
                            leakage.get(
                                "reserve_validation_patient_ids",
                                [],
                            ),
                        )
                    )
                )
            ),
            (
                "- remaining reserve patients sealed: "
                + str(
                    len(
                        cast(
                            list[object],
                            leakage.get(
                                "remaining_reserve_patient_ids",
                                [],
                            ),
                        )
                    )
                )
            ),
            "- untouched holdout t2 loaded: false",
            "",
            "## Next step",
            "",
            str(
                manifest.get(
                    "next_step",
                    "",
                )
            ),
            "",
        ]
    )

    return "\n".join(
        lines
    )


def write_stage10_validation_markdown_report(
    result_root: Path,
) -> Path:
    root = (
        result_root.resolve()
    )

    manifest_path = (
        root
        / "stage10_internal_validation.json"
    )

    seal_path = (
        root
        / "stage10_internal_validation.sha256"
    )

    if (
        not manifest_path.is_file()
        or not seal_path.is_file()
    ):
        raise FileNotFoundError(
            "Stage 10 validation artifact is incomplete"
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
            "Stage 10 validation checksum mismatch"
        )

    raw: object = json.loads(
        manifest_path.read_text(
            encoding="utf-8"
        )
    )

    manifest = _mapping(
        raw,
        name="manifest",
    )

    destination = (
        root
        / "STAGE10_VALIDATION_RESULT.md"
    )

    destination.write_text(
        render_stage10_validation_markdown(
            manifest
        ),
        encoding="utf-8",
    )

    return destination
