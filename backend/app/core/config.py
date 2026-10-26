import secrets
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

INSECURE_JWT_SECRETS = {
    "dev-change-me",
    "secret",
    "changeme",
    "jwt-secret",
    "123456",
    "password",
    "default",
    "admin",
    "replace-with-secure-random-secret-at-least-32-chars",
    "<generate_secure_random_secret_min_32_chars>",
}


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./power_monitoring.db"

    ENVIRONMENT: str = "development"
    AUTH_ENABLED: bool = True
    JWT_SECRET: str | None = None
    JWT_EXPIRE_MINUTES: int = 1440
    ADMIN_USERNAME: str | None = None
    ADMIN_PASSWORD: str | None = None
    INGEST_API_KEY: str | None = None

    DEVICE_OFFLINE_SECONDS: int = 120
    CLOCK_SKEW_TOLERANCE_SECONDS: int = 60

    NOMINAL_PHASE_VOLTAGE: float = 230.0
    UNDERVOLTAGE_RATIO: float = 0.85
    OVERVOLTAGE_RATIO: float = 1.10
    VOLTAGE_ABSENT_MAX: float = 15.0
    OVERCURRENT_AMPS: float | None = None
    HIGH_TEMPERATURE_C: float | None = None
    IMBALANCE_PERCENT: float = 10.0
    SUDDEN_VOLTAGE_DELTA: float | None = None
    SUDDEN_CURRENT_DELTA: float | None = None
    SUDDEN_POWER_DELTA: float | None = None
    SUDDEN_PF_DELTA: float | None = None
    SUDDEN_FREQUENCY_DELTA: float | None = None
    SUDDEN_TEMPERATURE_DELTA: float | None = None
    FREQUENCY_NOMINAL: float = 50.0
    FREQUENCY_TOLERANCE_HZ: float | None = None

    ML_ENABLED: bool = False
    ML_DEMO: bool = False

    @model_validator(mode="after")
    def validate_security_settings(self) -> "Settings":
        env = (self.ENVIRONMENT or "development").strip().lower()
        if env in {"production", "prod", "staging"}:
            if not self.JWT_SECRET or self.JWT_SECRET.strip() in INSECURE_JWT_SECRETS or len(self.JWT_SECRET.strip()) < 32:
                raise ValueError(
                    "Production security configuration error: JWT_SECRET must be set in environment "
                    "to a strong, non-default secret of at least 32 characters."
                )
        else:
            if not self.JWT_SECRET or not self.JWT_SECRET.strip():
                # Provide a persistent development default or ephemeral secret if not supplied
                self.JWT_SECRET = "dev-insecure-test-key-only-not-for-production-use-32chars"
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

