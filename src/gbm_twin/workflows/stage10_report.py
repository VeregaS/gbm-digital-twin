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


def _list(
    value: object,
    *,
    name: str,
) -> list[object]:
    if not isinstance(
        value,
        list,
    ):
        raise ValueError(
            f"{name} must be a list"
        )

    return cast(
        list[object],
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

    if type(value) is not int:
        raise ValueError(
            f"{key} must be an integer"
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


def render_stage10_markdown(
    manifest: dict[str, object],
) -> str:
    if (
        manifest.get(
            "sealed"
        )
        is not True
    ):
        raise ValueError(
            "Stage 10 artifact must be sealed"
        )

    decision = str(
        manifest.get(
            "decision",
            "",
        )
    ).strip()

    if decision not in {
        "decoupled_candidate_advanced",
        "no_decoupled_candidate_advanced",
    }:
        raise ValueError(
            "Unsupported Stage 10 decision"
        )

    control = _mapping(
        manifest.get(
            "control_summary"
        ),
        name="control_summary",
    )

    selected = _mapping(
        manifest.get(
            "selected_summary"
        ),
        name="selected_summary",
    )

    raw_candidates = _list(
        manifest.get(
            "candidate_summaries"
        ),
        name="candidate_summaries",
    )

    candidates = [
        _mapping(
            value,
            name="candidate_summary",
        )
        for value in raw_candidates
    ]

    selected_id = str(
        selected.get(
            "candidate_id",
            "",
        )
    )

    if not selected_id:
        raise ValueError(
            "selected candidate id is empty"
        )

    if (
        decision
        == "decoupled_candidate_advanced"
    ):
        conclusion = (
            "A pre-specified decoupled candidate passed the Stage 10 "
            "advancement guardrails. Freeze this model structure before "
            "opening any reserve patient."
        )

        next_step = (
            "Freeze the selected Stage 10 structure and prepare a "
            "pre-specified reserve-validation plan."
        )

    else:
        conclusion = (
            "No decoupled candidate passed the Stage 10 advancement "
            "guardrails. Do not add further RT compartments."
        )

        next_step = (
            "Move the next development cycle to the MRI observation model, "
            "defensible multimodal representation and uncertainty."
        )

    lines = [
        "# Stage 10 — sealed development result",
        "",
        f"Decision: `{decision}`",
        "",
        f"Selected candidate: `{selected_id}`",
        "",
        conclusion,
        "",
        "## Summary",
        "",
        "| Candidate | Kind | Mean Dice | Δ vs persistence | Catastrophic | Regression Δ | Growth Δ | RVE | HD95 mm |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    for candidate in candidates:
        lines.append(
            "| "
            + str(
                candidate.get(
                    "candidate_id",
                    "",
                )
            )
            + " | "
            + str(
                candidate.get(
                    "candidate_kind",
                    "",
                )
            )
            + " | "
            + _fmt(
                _number(
                    candidate,
                    "mean_dice",
                )
            )
            + " | "
            + _fmt(
                _number(
                    candidate,
                    "mean_delta_vs_persistence",
                ),
                signed=True,
            )
            + " | "
            + str(
                _integer(
                    candidate,
                    "catastrophic_failure_count",
                )
            )
            + " | "
            + _fmt(
                _optional_number(
                    candidate,
                    "regression_mean_delta_vs_persistence",
                ),
                signed=True,
            )
            + " | "
            + _fmt(
                _optional_number(
                    candidate,
                    "growth_mean_delta_vs_persistence",
                ),
                signed=True,
            )
            + " | "
            + _fmt(
                _number(
                    candidate,
                    "mean_relative_volume_error",
                )
            )
            + " | "
            + _fmt(
                _optional_number(
                    candidate,
                    "mean_hd95_mm",
                )
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Control check",
            "",
            (
                "- Stage 9 control mean Dice: "
                + _fmt(
                    _number(
                        control,
                        "mean_dice",
                    )
                )
            ),
            (
                "- Stage 9 control catastrophic failures: "
                + str(
                    _integer(
                        control,
                        "catastrophic_failure_count",
                    )
                )
            ),
            (
                "- Selected mean Dice: "
                + _fmt(
                    _number(
                        selected,
                        "mean_dice",
                    )
                )
            ),
            (
                "- Selected catastrophic failures: "
                + str(
                    _integer(
                        selected,
                        "catastrophic_failure_count",
                    )
                )
            ),
            "",
            "## Next scientific step",
            "",
            next_step,
            "",
            (
                "Reserve patients and untouched holdout remain sealed. "
                "This report summarizes the already-exposed development cohort only."
            ),
            "",
        ]
    )

    return "\n".join(
        lines
    )


def write_stage10_markdown_report(
    result_root: Path,
) -> Path:
    root = (
        result_root.resolve()
    )

    manifest_path = (
        root
        / "stage10_decoupled_selection.json"
    )

    seal_path = (
        root
        / "stage10_decoupled_selection.sha256"
    )

    if (
        not manifest_path.is_file()
        or not seal_path.is_file()
    ):
        raise FileNotFoundError(
            "Stage 10 sealed artifact is incomplete"
        )

    expected_tokens = (
        seal_path.read_text(
            encoding="ascii"
        ).split()
    )

    actual_sha = (
        sha256_file(
            manifest_path
        )
    )

    if (
        not expected_tokens
        or expected_tokens[0]
        != actual_sha
    ):
        raise ValueError(
            "Stage 10 artifact checksum mismatch"
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
        / "STAGE10_RESULT.md"
    )

    destination.write_text(
        render_stage10_markdown(
            manifest
        ),
        encoding="utf-8",
    )

    return destination
