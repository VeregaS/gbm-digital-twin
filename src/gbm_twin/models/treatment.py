from dataclasses import dataclass


@dataclass(frozen=True)
class TreatmentWindow:
    start_day: float
    end_day: float
    kill_rate: float

    def __post_init__(self) -> None:
        if self.start_day < 0:
            raise ValueError(
                "Treatment start day must be non-negative"
            )

        if self.end_day <= self.start_day:
            raise ValueError(
                "Treatment end day must be greater "
                "than treatment start day"
            )

        if self.kill_rate < 0:
            raise ValueError(
                "Treatment kill rate must be non-negative"
            )

    def kill_rate_at(
        self,
        time_day: float,
    ) -> float:
        if time_day < 0:
            raise ValueError(
                "Simulation time must be non-negative"
            )

        if (
            self.start_day
            <= time_day
            < self.end_day
        ):
            return self.kill_rate

        return 0.0