from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Thresholds:
    """Monitoring bands, not protection ratings.

    Values are site configuration. Confirm them against the installation
    before treating detections as operational truth.
    """

    nominal_phase_voltage: float = 230.0
    undervoltage_ratio: float = 0.85
    overvoltage_ratio: float = 1.10
    voltage_absent_max: float = 15.0
    overcurrent_amps: float | None = None
    high_temperature_c: float | None = None
    imbalance_percent: float = 10.0
    sudden_voltage_delta: float | None = None
    sudden_current_delta: float | None = None
    sudden_power_delta: float | None = None
    sudden_pf_delta: float | None = None
    sudden_frequency_delta: float | None = None
    sudden_temperature_delta: float | None = None
    frequency_nominal: float = 50.0
    frequency_tolerance_hz: float | None = None

    @property
    def undervoltage_volts(self) -> float:
        return self.nominal_phase_voltage * self.undervoltage_ratio

    @property
    def overvoltage_volts(self) -> float:
        return self.nominal_phase_voltage * self.overvoltage_ratio


def thresholds_from_settings(settings: Any) -> Thresholds:
    return Thresholds(
        nominal_phase_voltage=settings.NOMINAL_PHASE_VOLTAGE,
        undervoltage_ratio=settings.UNDERVOLTAGE_RATIO,
        overvoltage_ratio=settings.OVERVOLTAGE_RATIO,
        voltage_absent_max=settings.VOLTAGE_ABSENT_MAX,
        overcurrent_amps=settings.OVERCURRENT_AMPS,
        high_temperature_c=settings.HIGH_TEMPERATURE_C,
        imbalance_percent=settings.IMBALANCE_PERCENT,
        sudden_voltage_delta=settings.SUDDEN_VOLTAGE_DELTA,
        sudden_current_delta=settings.SUDDEN_CURRENT_DELTA,
        sudden_power_delta=settings.SUDDEN_POWER_DELTA,
        sudden_pf_delta=settings.SUDDEN_PF_DELTA,
        sudden_frequency_delta=settings.SUDDEN_FREQUENCY_DELTA,
        sudden_temperature_delta=settings.SUDDEN_TEMPERATURE_DELTA,
        frequency_nominal=settings.FREQUENCY_NOMINAL,
        frequency_tolerance_hz=settings.FREQUENCY_TOLERANCE_HZ,
    )
