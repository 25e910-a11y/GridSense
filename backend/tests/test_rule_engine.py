from app.rules.engine import PhaseSample, evaluate_telemetry
from app.rules.thresholds import Thresholds


def _thresholds(**overrides) -> Thresholds:
    values = dict(
        nominal_phase_voltage=230.0,
        undervoltage_ratio=0.85,
        overvoltage_ratio=1.10,
        voltage_absent_max=15.0,
        overcurrent_amps=32.0,
        high_temperature_c=60.0,
        imbalance_percent=10.0,
        sudden_voltage_delta=40.0,
        sudden_current_delta=8.0,
        frequency_nominal=50.0,
        frequency_tolerance_hz=2.5,
    )
    values.update(overrides)
    return Thresholds(**values)


def test_normal_sample_creates_no_findings():
    sample = PhaseSample(phase="R", voltage=230, current=5, power=1000, frequency=50, power_factor=0.95, data_quality="good")
    assert evaluate_telemetry(sample, _thresholds()) == []


def test_comm_quality_is_not_phase_loss():
    sample = PhaseSample(phase="R", voltage=0, data_quality="comm_error")
    findings = evaluate_telemetry(sample, _thresholds())
    assert len(findings) == 1
    assert findings[0].fault_type == "SENSOR_COMMUNICATION"
    assert findings[0].category == "sensor_communication"


def test_missing_values_are_not_phase_loss():
    sample = PhaseSample(phase="Y", data_quality="good")
    findings = evaluate_telemetry(sample, _thresholds())
    assert findings[0].fault_type == "SENSOR_COMMUNICATION"


def test_loss_of_voltage_requires_other_healthy_phases():
    sample = PhaseSample(phase="R", voltage=2, data_quality="good")
    others = [
        PhaseSample(phase="Y", voltage=229, data_quality="good"),
        PhaseSample(phase="B", voltage=231, data_quality="good"),
    ]
    findings = evaluate_telemetry(sample, _thresholds(), other_phases=others)
    types = {item.fault_type for item in findings}
    assert "LOSS_OF_VOLTAGE" in types
    assert "SENSOR_COMMUNICATION" not in types


def test_near_zero_voltage_without_other_phases_is_not_phase_loss():
    sample = PhaseSample(phase="R", voltage=2, data_quality="good")
    findings = evaluate_telemetry(sample, _thresholds(), other_phases=[])
    assert findings[0].fault_type == "SENSOR_COMMUNICATION"


def test_overvoltage_and_undervoltage():
    high = PhaseSample(phase="R", voltage=270, data_quality="good")
    low = PhaseSample(phase="Y", voltage=180, data_quality="good")
    assert evaluate_telemetry(high, _thresholds())[0].fault_type == "OVERVOLTAGE"
    assert evaluate_telemetry(low, _thresholds())[0].fault_type == "UNDERVOLTAGE"


def test_overcurrent_skipped_when_limit_not_configured():
    sample = PhaseSample(phase="R", voltage=230, current=80, data_quality="good")
    findings = evaluate_telemetry(sample, _thresholds(overcurrent_amps=None))
    assert findings == []


def test_invalid_power_factor_is_sensor_issue():
    sample = PhaseSample(phase="B", voltage=230, power_factor=1.4, data_quality="good")
    findings = evaluate_telemetry(sample, _thresholds())
    assert findings[0].fault_type == "INVALID_MEASUREMENT"
    assert findings[0].category == "sensor_communication"


def test_phase_imbalance():
    sample = PhaseSample(phase="R", voltage=230, data_quality="good")
    others = [
        PhaseSample(phase="Y", voltage=230, data_quality="good"),
        PhaseSample(phase="B", voltage=180, data_quality="good"),
    ]
    types = {item.fault_type for item in evaluate_telemetry(sample, _thresholds(), other_phases=others)}
    assert "PHASE_IMBALANCE" in types
