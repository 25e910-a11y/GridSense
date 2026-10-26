from __future__ import annotations

from dataclasses import dataclass

from app.rules.thresholds import Thresholds

SENSOR_QUALITY_TOKENS = {
    "bad",
    "error",
    "invalid",
    "comm_error",
    "sensor_error",
    "timeout",
    "offline",
}

USABLE_QUALITY_TOKENS = {
    None,
    "good",
    "ok",
    "valid",
    "estimated",
}

CATEGORY_SENSOR = "sensor_communication"
CATEGORY_ELECTRICAL = "electrical"


@dataclass(frozen=True)
class Finding:
    fault_type: str
    category: str
    severity: str
    phase: str | None
    measured_value: float | None
    expected_value: float | None
    unit: str | None
    description: str


@dataclass(frozen=True)
class PhaseSample:
    phase: str
    voltage: float | None = None
    current: float | None = None
    power: float | None = None
    frequency: float | None = None
    power_factor: float | None = None
    temperature: float | None = None
    data_quality: str | None = None


def evaluate_telemetry(
    sample: PhaseSample,
    thresholds: Thresholds,
    previous: PhaseSample | None = None,
    other_phases: list[PhaseSample] | None = None,
) -> list[Finding]:
    """Classify one sample. Sensor/comm findings suppress electrical ones."""

    findings: list[Finding] = []
    quality = _normalize_quality(sample.data_quality)

    if quality in SENSOR_QUALITY_TOKENS:
        findings.append(
            Finding(
                fault_type="SENSOR_COMMUNICATION",
                category=CATEGORY_SENSOR,
                severity="warning",
                phase=sample.phase,
                measured_value=None,
                expected_value=None,
                unit=None,
                description=(
                    f"Reported data_quality={quality} for phase {sample.phase}. "
                    "Not classified as an electrical abnormality."
                ),
            )
        )
        return findings

    invalid = _invalid_measurement_findings(sample)
    if invalid:
        return invalid

    if quality not in USABLE_QUALITY_TOKENS:
        findings.append(
            Finding(
                fault_type="SENSOR_COMMUNICATION",
                category=CATEGORY_SENSOR,
                severity="warning",
                phase=sample.phase,
                measured_value=None,
                expected_value=None,
                unit=None,
                description=(
                    f"Unrecognised data_quality={quality} for phase {sample.phase}. "
                    "Not classified as an electrical abnormality."
                ),
            )
        )
        return findings

    if _all_electrical_missing(sample):
        findings.append(
            Finding(
                fault_type="SENSOR_COMMUNICATION",
                category=CATEGORY_SENSOR,
                severity="warning",
                phase=sample.phase,
                measured_value=None,
                expected_value=None,
                unit=None,
                description=(
                    f"No electrical values present for phase {sample.phase}. "
                    "Treated as a sensor/communication issue, not phase loss."
                ),
            )
        )
        return findings

    findings.extend(_electrical_findings(sample, thresholds, previous, other_phases or []))
    return findings


def _normalize_quality(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip().lower()


def _all_electrical_missing(sample: PhaseSample) -> bool:
    return all(
        value is None
        for value in (
            sample.voltage,
            sample.current,
            sample.power,
            sample.frequency,
            sample.power_factor,
        )
    )


def _invalid_measurement_findings(sample: PhaseSample) -> list[Finding]:
    findings: list[Finding] = []

    checks = [
        ("voltage", sample.voltage, lambda v: v < 0),
        ("current", sample.current, lambda v: v < 0),
        ("power", sample.power, lambda v: v < 0),
        ("frequency", sample.frequency, lambda v: v < 0),
        ("power_factor", sample.power_factor, lambda v: v < 0 or v > 1),
    ]

    for name, value, invalid in checks:
        if value is not None and invalid(value):
            findings.append(
                Finding(
                    fault_type="INVALID_MEASUREMENT",
                    category=CATEGORY_SENSOR,
                    severity="warning",
                    phase=sample.phase,
                    measured_value=value,
                    expected_value=None,
                    unit=name,
                    description=(
                        f"Implausible {name}={value} on phase {sample.phase}. "
                        "Treated as a data/sensor issue, not an electrical fault."
                    ),
                )
            )

    return findings


def _electrical_findings(
    sample: PhaseSample,
    thresholds: Thresholds,
    previous: PhaseSample | None,
    other_phases: list[PhaseSample],
) -> list[Finding]:
    findings: list[Finding] = []

    if sample.voltage is not None:
        if sample.voltage <= thresholds.voltage_absent_max:
            if _other_phases_have_voltage(other_phases, thresholds):
                findings.append(
                    Finding(
                        fault_type="LOSS_OF_VOLTAGE",
                        category=CATEGORY_ELECTRICAL,
                        severity="fault",
                        phase=sample.phase,
                        measured_value=sample.voltage,
                        expected_value=thresholds.nominal_phase_voltage,
                        unit="V",
                        description=(
                            f"Phase {sample.phase} voltage {sample.voltage} V is at or below "
                            f"{thresholds.voltage_absent_max} V while other phases still show "
                            "usable voltage. Classified as inferred loss of voltage."
                        ),
                    )
                )
            else:
                findings.append(
                    Finding(
                        fault_type="SENSOR_COMMUNICATION",
                        category=CATEGORY_SENSOR,
                        severity="warning",
                        phase=sample.phase,
                        measured_value=sample.voltage,
                        expected_value=thresholds.nominal_phase_voltage,
                        unit="V",
                        description=(
                            f"Phase {sample.phase} voltage {sample.voltage} V is near zero, "
                            "but other phases do not confirm a healthy supply. "
                            "Not classified as phase loss."
                        ),
                    )
                )
        elif sample.voltage < thresholds.undervoltage_volts:
            findings.append(
                Finding(
                    fault_type="UNDERVOLTAGE",
                    category=CATEGORY_ELECTRICAL,
                    severity="warning",
                    phase=sample.phase,
                    measured_value=sample.voltage,
                    expected_value=thresholds.undervoltage_volts,
                    unit="V",
                    description=(
                        f"Phase {sample.phase} voltage {sample.voltage} V is below the "
                        f"configured monitoring band {thresholds.undervoltage_volts:.1f} V."
                    ),
                )
            )
        elif sample.voltage > thresholds.overvoltage_volts:
            findings.append(
                Finding(
                    fault_type="OVERVOLTAGE",
                    category=CATEGORY_ELECTRICAL,
                    severity="warning",
                    phase=sample.phase,
                    measured_value=sample.voltage,
                    expected_value=thresholds.overvoltage_volts,
                    unit="V",
                    description=(
                        f"Phase {sample.phase} voltage {sample.voltage} V is above the "
                        f"configured monitoring band {thresholds.overvoltage_volts:.1f} V."
                    ),
                )
            )

    if (
        sample.current is not None
        and thresholds.overcurrent_amps is not None
        and sample.current > thresholds.overcurrent_amps
    ):
        findings.append(
            Finding(
                fault_type="OVERCURRENT",
                category=CATEGORY_ELECTRICAL,
                severity="fault",
                phase=sample.phase,
                measured_value=sample.current,
                expected_value=thresholds.overcurrent_amps,
                unit="A",
                description=(
                    f"Phase {sample.phase} current {sample.current} A exceeds the "
                    f"configured monitoring limit {thresholds.overcurrent_amps} A."
                ),
            )
        )

    if (
        sample.temperature is not None
        and thresholds.high_temperature_c is not None
        and sample.temperature >= thresholds.high_temperature_c
    ):
        findings.append(
            Finding(
                fault_type="HIGH_TEMPERATURE",
                category=CATEGORY_ELECTRICAL,
                severity="warning",
                phase=sample.phase,
                measured_value=sample.temperature,
                expected_value=thresholds.high_temperature_c,
                unit="°C",
                description=(
                    f"Temperature {sample.temperature} °C is at or above the configured "
                    f"monitoring limit {thresholds.high_temperature_c} °C."
                ),
            )
        )

    if (
        sample.frequency is not None
        and thresholds.frequency_tolerance_hz is not None
        and abs(sample.frequency - thresholds.frequency_nominal)
        > thresholds.frequency_tolerance_hz
    ):
        findings.append(
            Finding(
                fault_type="FREQUENCY_ABNORMAL",
                category=CATEGORY_ELECTRICAL,
                severity="warning",
                phase=sample.phase,
                measured_value=sample.frequency,
                expected_value=thresholds.frequency_nominal,
                unit="Hz",
                description=(
                    f"Phase {sample.phase} frequency {sample.frequency} Hz is outside "
                    f"{thresholds.frequency_nominal} ± {thresholds.frequency_tolerance_hz} Hz."
                ),
            )
        )

    if previous is not None:
        findings.extend(_sudden_change_findings(sample, previous, thresholds))

    findings.extend(_imbalance_findings(sample, other_phases, thresholds))
    return findings


def _other_phases_have_voltage(
    other_phases: list[PhaseSample],
    thresholds: Thresholds,
) -> bool:
    healthy = 0
    for other in other_phases:
        if other.voltage is None:
            continue
        if _normalize_quality(other.data_quality) in SENSOR_QUALITY_TOKENS:
            continue
        if other.voltage > thresholds.voltage_absent_max:
            healthy += 1
    return healthy >= 1


def _sudden_change_findings(
    sample: PhaseSample,
    previous: PhaseSample,
    thresholds: Thresholds,
) -> list[Finding]:
    findings: list[Finding] = []
    checks = [
        (
            thresholds.sudden_voltage_delta,
            sample.voltage,
            previous.voltage,
            "SUDDEN_VOLTAGE_CHANGE",
            "V",
            "voltage",
        ),
        (
            thresholds.sudden_current_delta,
            sample.current,
            previous.current,
            "SUDDEN_CURRENT_CHANGE",
            "A",
            "current",
        ),
        (
            thresholds.sudden_power_delta,
            sample.power,
            previous.power,
            "SUDDEN_POWER_CHANGE",
            "W",
            "power",
        ),
        (
            thresholds.sudden_pf_delta,
            sample.power_factor,
            previous.power_factor,
            "SUDDEN_PF_CHANGE",
            None,
            "power factor",
        ),
        (
            thresholds.sudden_frequency_delta,
            sample.frequency,
            previous.frequency,
            "SUDDEN_FREQUENCY_CHANGE",
            "Hz",
            "frequency",
        ),
        (
            thresholds.sudden_temperature_delta,
            sample.temperature,
            previous.temperature,
            "SUDDEN_TEMPERATURE_CHANGE",
            "°C",
            "temperature",
        ),
    ]

    for limit, current, previous_value, fault_type, unit, label in checks:
        if (
            limit is None
            or current is None
            or previous_value is None
            or abs(current - previous_value) < limit
        ):
            continue
        findings.append(
            Finding(
                fault_type=fault_type,
                category=CATEGORY_ELECTRICAL,
                severity="warning",
                phase=sample.phase,
                measured_value=current,
                expected_value=previous_value,
                unit=unit,
                description=(
                    f"Phase {sample.phase} {label} changed from {previous_value} to "
                    f"{current} (configured delta {limit}{(' ' + unit) if unit else ''})."
                ),
            )
        )

    return findings


def _imbalance_findings(
    sample: PhaseSample,
    other_phases: list[PhaseSample],
    thresholds: Thresholds,
) -> list[Finding]:
    voltages: list[tuple[str, float]] = []
    if sample.voltage is not None and sample.voltage > thresholds.voltage_absent_max:
        voltages.append((sample.phase, sample.voltage))

    for other in other_phases:
        if other.voltage is None or other.voltage <= thresholds.voltage_absent_max:
            continue
        if _normalize_quality(other.data_quality) in SENSOR_QUALITY_TOKENS:
            continue
        voltages.append((other.phase, other.voltage))

    unique_phases = {phase for phase, _ in voltages}
    if len(unique_phases) < 3:
        return []

    values = [value for _, value in voltages]
    average = sum(values) / len(values)
    if average <= 0:
        return []

    max_deviation = max(abs(value - average) / average * 100 for value in values)
    if max_deviation < thresholds.imbalance_percent:
        return []

    return [
        Finding(
            fault_type="PHASE_IMBALANCE",
            category=CATEGORY_ELECTRICAL,
            severity="warning",
            phase=sample.phase,
            measured_value=round(max_deviation, 2),
            expected_value=thresholds.imbalance_percent,
            unit="%",
            description=(
                f"Phase voltages {voltages} deviate {max_deviation:.1f}% from the mean, "
                f"above the configured imbalance band {thresholds.imbalance_percent}%."
            ),
        )
    ]
