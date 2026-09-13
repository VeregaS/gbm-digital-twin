from dataclasses import dataclass


@dataclass(frozen=True)
class RadiobiologyParameters:
    alpha_per_gy: float
    alpha_beta_ratio_gy: float

    def __post_init__(self) -> None:
        if self.alpha_per_gy < 0:
            raise ValueError(
                "Alpha must be non-negative"
            )

        if self.alpha_beta_ratio_gy <= 0:
            raise ValueError(
                "Alpha/beta ratio must be positive"
            )

    @property
    def beta_per_gy2(self) -> float:
        return (
            self.alpha_per_gy
            / self.alpha_beta_ratio_gy
        )