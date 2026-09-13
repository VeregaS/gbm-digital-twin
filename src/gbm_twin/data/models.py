from dataclasses import dataclass, field
from pathlib import Path

from gbm_twin.data.nifti import NiftiVolume


@dataclass(frozen=True)
class Timepoint:
    name: str
    days_from_baseline: int | None = None

    t1gd_path: Path | None = None
    flair_path: Path | None = None
    gtv_path: Path | None = None


@dataclass
class Patient:
    patient_id: str
    timepoints: dict[str, Timepoint] = field(default_factory=dict)

    def add_timepoint(self, timepoint: Timepoint) -> None:
        if timepoint.name in self.timepoints:
            raise ValueError(
                f"Timepoint '{timepoint.name}' already exists "
                f"for patient '{self.patient_id}'"
            )

        self.timepoints[timepoint.name] = timepoint

    def get_timepoint(self, name: str) -> Timepoint:
        try:
            return self.timepoints[name]
        except KeyError as exc:
            raise KeyError(
                f"Patient '{self.patient_id}' has no timepoint '{name}'"
            ) from exc
            
    def interval_days(self, start: str, end: str) -> int:
        start_timepoint = self.get_timepoint(start)
        end_timepoint = self.get_timepoint(end)

        if (
            start_timepoint.days_from_baseline is None
            or end_timepoint.days_from_baseline is None
        ):
            raise ValueError("Both timepoints must have days_from_baseline")

        interval = (
            end_timepoint.days_from_baseline
            - start_timepoint.days_from_baseline
        )

        if interval <= 0:
            raise ValueError(
                f"Invalid time interval: {start} -> {end} = {interval} days"
            )

        return interval
    

@dataclass(frozen=True)
class PatientTimepointStudy:
    patient_id: str
    timepoint: Timepoint
    t1gd: NiftiVolume
    gtv: NiftiVolume
    brain_mask: NiftiVolume
