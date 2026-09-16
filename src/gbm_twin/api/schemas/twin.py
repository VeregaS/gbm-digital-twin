from __future__ import annotations

from pydantic import BaseModel

from gbm_twin.workflows.cohort_evaluation import (
    CohortEvaluationPayload,
    MethodMetricsPayload,
    PatientEvaluationPayload,
)
from gbm_twin.workflows.cohort_results import (
    CohortEvaluationSummary,
    CohortMethodSummary,
)


class TwinDatasetResponse(BaseModel):
    name: str
    version: int
    doi: str


class TwinRepositoryResponse(BaseModel):
    commit_sha: str
    dirty: bool


class TwinMethodMetricsResponse(BaseModel):
    dice: float
    relative_volume_error: float

    hd95_mm: float | None

    centroid_distance_mm: (
        float | None
    )

    @classmethod
    def from_payload(
        cls,
        payload: MethodMetricsPayload,
    ) -> TwinMethodMetricsResponse:
        return cls(
            dice=payload["dice"],
            relative_volume_error=(
                payload[
                    "relative_volume_error"
                ]
            ),
            hd95_mm=payload[
                "hd95_mm"
            ],
            centroid_distance_mm=(
                payload[
                    "centroid_distance_mm"
                ]
            ),
        )


class TwinPatientEvaluationResponse(
    BaseModel
):
    patient_id: int

    target_timepoint: str
    target_day: float

    twin: TwinMethodMetricsResponse

    persistence: (
        TwinMethodMetricsResponse
    )

    volume_baseline: (
        TwinMethodMetricsResponse
    )

    @classmethod
    def from_payload(
        cls,
        payload: PatientEvaluationPayload,
    ) -> TwinPatientEvaluationResponse:
        return cls(
            patient_id=(
                payload["patient_id"]
            ),
            target_timepoint=(
                payload[
                    "target_timepoint"
                ]
            ),
            target_day=(
                payload["target_day"]
            ),
            twin=(
                TwinMethodMetricsResponse
                .from_payload(
                    payload["twin"]
                )
            ),
            persistence=(
                TwinMethodMetricsResponse
                .from_payload(
                    payload[
                        "persistence"
                    ]
                )
            ),
            volume_baseline=(
                TwinMethodMetricsResponse
                .from_payload(
                    payload[
                        "volume_baseline"
                    ]
                )
            ),
        )


class TwinPatientListItemResponse(
    BaseModel
):
    patient_id: int
    target_timepoint: str
    target_day: float


class TwinPatientListResponse(
    BaseModel
):
    patients: list[
        TwinPatientListItemResponse
    ]


class TwinMethodSummaryResponse(
    BaseModel
):
    patient_count: int

    hd95_count: int
    centroid_distance_count: int

    mean_dice: float | None

    mean_relative_volume_error: (
        float | None
    )

    mean_hd95_mm: float | None

    mean_centroid_distance_mm: (
        float | None
    )

    @classmethod
    def from_summary(
        cls,
        summary: CohortMethodSummary,
    ) -> TwinMethodSummaryResponse:
        return cls(
            patient_count=(
                summary.patient_count
            ),
            hd95_count=(
                summary.hd95_count
            ),
            centroid_distance_count=(
                summary
                .centroid_distance_count
            ),
            mean_dice=(
                summary.mean_dice
            ),
            mean_relative_volume_error=(
                summary
                .mean_relative_volume_error
            ),
            mean_hd95_mm=(
                summary.mean_hd95_mm
            ),
            mean_centroid_distance_mm=(
                summary
                .mean_centroid_distance_mm
            ),
        )


class TwinCohortResponse(BaseModel):
    schema_version: int

    dataset: TwinDatasetResponse
    repository: TwinRepositoryResponse

    target_spacing: list[float]

    patient_count: int

    twin: TwinMethodSummaryResponse

    persistence: (
        TwinMethodSummaryResponse
    )

    volume_baseline: (
        TwinMethodSummaryResponse
    )

    twin_better_than_persistence_count: int

    twin_equal_to_persistence_count: int

    twin_worse_than_persistence_count: int

    @classmethod
    def from_payload(
        cls,
        payload: CohortEvaluationPayload,
        summary: CohortEvaluationSummary,
    ) -> TwinCohortResponse:
        dataset = payload["dataset"]

        repository = (
            payload["repository"]
        )

        return cls(
            schema_version=(
                payload[
                    "schema_version"
                ]
            ),
            dataset=TwinDatasetResponse(
                name=dataset["name"],
                version=dataset["version"],
                doi=dataset["doi"],
            ),
            repository=(
                TwinRepositoryResponse(
                    commit_sha=(
                        repository[
                            "commit_sha"
                        ]
                    ),
                    dirty=(
                        repository["dirty"]
                    ),
                )
            ),
            target_spacing=(
                payload["target_spacing"]
            ),
            patient_count=(
                summary.patient_count
            ),
            twin=(
                TwinMethodSummaryResponse
                .from_summary(
                    summary.twin
                )
            ),
            persistence=(
                TwinMethodSummaryResponse
                .from_summary(
                    summary.persistence
                )
            ),
            volume_baseline=(
                TwinMethodSummaryResponse
                .from_summary(
                    summary
                    .volume_baseline
                )
            ),
            twin_better_than_persistence_count=(
                summary
                .twin_better_than_persistence_count
            ),
            twin_equal_to_persistence_count=(
                summary
                .twin_equal_to_persistence_count
            ),
            twin_worse_than_persistence_count=(
                summary
                .twin_worse_than_persistence_count
            ),
        )