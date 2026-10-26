from datetime import datetime

from pydantic import BaseModel, Field, field_validator


ALLOWED_PHASES = {"R", "Y", "B"}


class TelemetryCreate(BaseModel):
    device_id: int
    phase: str = Field(min_length=1, max_length=10)

    voltage: float | None = None
    current: float | None = None
    power: float | None = None
    energy: float | None = None
    power_factor: float | None = None
    frequency: float | None = None

    temperature: float | None = None

    sampled_at: datetime

    sampling_interval_ms: int | None = None

    transmission_reason: str = "SCHEDULED"
    source: str = "REAL"
    data_quality: str | None = "good"

    @field_validator("phase")
    @classmethod
    def normalize_phase(cls, value: str) -> str:
        phase = value.strip().upper()
        if phase not in ALLOWED_PHASES:
            raise ValueError("phase must be one of R, Y, B")
        return phase

    @field_validator("source")
    @classmethod
    def normalize_source(cls, value: str) -> str:
        source = value.strip().upper()
        allowed = {"REAL", "SIMULATION", "TEST"}
        if source not in allowed:
            raise ValueError("source must be REAL, SIMULATION, or TEST")
        return source

    @field_validator("transmission_reason")
    @classmethod
    def normalize_reason(cls, value: str) -> str:
        return value.strip().upper()
