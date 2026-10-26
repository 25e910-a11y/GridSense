from app.schemas.telemetry import TelemetryCreate

TRANSMISSION_REASONS = {
    "SCHEDULED",
    "PARAMETER_CHANGE",
    "FAULT_EVENT",
    "RELAY_EVENT",
    "DEVICE_EVENT",
}


def assess_telemetry(data: TelemetryCreate) -> tuple[str, list[str]]:
    issues: list[str] = []
    reported = (data.data_quality or "good").strip().lower()

    if data.transmission_reason not in TRANSMISSION_REASONS:
        issues.append("unsupported transmission_reason")

    checks = [
        ("voltage", data.voltage, lambda value: value < 0),
        ("current", data.current, lambda value: value < 0),
        ("power", data.power, lambda value: value < 0),
        ("energy", data.energy, lambda value: value < 0),
        ("frequency", data.frequency, lambda value: value < 0),
        ("power_factor", data.power_factor, lambda value: value < 0 or value > 1),
    ]
    for name, value, invalid in checks:
        if value is not None and invalid(value):
            issues.append(f"implausible {name}")

    if reported in {"bad", "error", "invalid", "comm_error", "sensor_error", "timeout", "offline"}:
        return reported, issues

    if issues:
        return "invalid", issues

    return reported or "good", issues
