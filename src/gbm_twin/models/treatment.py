import math
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


@dataclass(frozen=True)
class PostRadiotherapyEffect:
    start_day: float
    initial_kill_rate: float
    decay_time_days: float

    def __post_init__(self) -> None:
        if self.start_day < 0:
            raise ValueError(
                "Post-RT start day must be non-negative"
            )

        if self.initial_kill_rate < 0:
            raise ValueError(
                "Initial kill rate must be non-negative"
            )

        if self.decay_time_days <= 0:
            raise ValueError(
                "Decay time must be positive"
            )

    def kill_rate_at(
        self,
        time_day: float,
    ) -> float:
        if time_day < 0:
            raise ValueError(
                "Simulation time must be non-negative"
            )

        if time_day < self.start_day:
            return 0.0

        elapsed = (
            time_day
            - self.start_day
        )

        return (
            self.initial_kill_rate
            * math.exp(
                -elapsed
                / self.decay_time_days
            )
        )


@dataclass(frozen=True)
class FractionatedRadiotherapy:
    fraction_days: tuple[float, ...]
    dose_per_fraction_gy: float
    alpha_per_gy: float
    beta_per_gy2: float

    def __post_init__(self) -> None:
        if not self.fraction_days:
            raise ValueError(
                "At least one radiotherapy fraction is required"
            )

        if any(
            day < 0
            for day in self.fraction_days
        ):
            raise ValueError(
                "Fraction days must be non-negative"
            )

        if any(
            current <= previous
            for previous, current
            in zip(
                self.fraction_days,
                self.fraction_days[1:],
                strict=False,
            )
        ):
            raise ValueError(
                "Fraction days must be strictly increasing"
            )

        if self.dose_per_fraction_gy <= 0:
            raise ValueError(
                "Dose per fraction must be positive"
            )

        if self.alpha_per_gy < 0:
            raise ValueError(
                "Alpha must be non-negative"
            )

        if self.beta_per_gy2 < 0:
            raise ValueError(
                "Beta must be non-negative"
            )

    @property
    def fractions_number(self) -> int:
        return len(
            self.fraction_days
        )

    @property
    def total_dose_gy(self) -> float:
        return (
            self.dose_per_fraction_gy
            * self.fractions_number
        )

    @property
    def survival_fraction_per_fraction(
        self,
    ) -> float:
        dose = self.dose_per_fraction_gy

        exponent = -(
            self.alpha_per_gy
            * dose
            + self.beta_per_gy2
            * dose**2
        )

        return math.exp(
            exponent
        )

    def has_fraction_at(
        self,
        time_day: float,
        *,
        tolerance: float = 1e-9,
    ) -> bool:
        if time_day < 0:
            raise ValueError(
                "Simulation time must be non-negative"
            )

        if tolerance < 0:
            raise ValueError(
                "Tolerance must be non-negative"
            )

        return any(
            math.isclose(
                time_day,
                fraction_day,
                rel_tol=0.0,
                abs_tol=tolerance,
            )
            for fraction_day
            in self.fraction_days
        )

    def survival_fraction_at(
        self,
        time_day: float,
    ) -> float:
        if self.has_fraction_at(
            time_day
        ):
            return (
                self.survival_fraction_per_fraction
            )

        return 1.0


@dataclass(frozen=True)
class RadiotherapyProtocol:
    fractions: FractionatedRadiotherapy
    post_effect: PostRadiotherapyEffect | None = None

    def __post_init__(self) -> None:
        if self.post_effect is None:
            return

        last_fraction_day = (
            self.fractions.fraction_days[-1]
        )

        if (
            self.post_effect.start_day
            < last_fraction_day
        ):
            raise ValueError(
                "Post-RT effect must not start "
                "before the last RT fraction"
            )