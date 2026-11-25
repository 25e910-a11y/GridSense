"""Per-device settings: alarm limits, alert mode and ingest keys."""

import hashlib
import secrets
from dataclasses import fields, replace
from typing import Any

from app.rules.thresholds import Thresholds, thresholds_from_settings

ALERT_MODES = ("alert", "log_only")

# Every Thresholds field can be overridden per device.
OVERRIDABLE_LIMITS = tuple(f.name for f in fields(Thresholds))


def clean_limits(limits: dict[str, Any] | None) -> dict[str, float]:
    """Keep only known limit names with numeric values."""
    if not limits:
        return {}
    cleaned: dict[str, float] = {}
    for key, value in limits.items():
        if key in OVERRIDABLE_LIMITS and isinstance(value, (int, float)) and not isinstance(value, bool):
            cleaned[key] = float(value)
    return cleaned


def thresholds_for_device(settings: Any, device: Any | None) -> Thresholds:
    """Site limits from config, with this device's overrides on top."""
    base = thresholds_from_settings(settings)
    if device is None:
        return base
    overrides = clean_limits(getattr(device, "alarm_limits", None))
    return replace(base, **overrides) if overrides else base


def alerts_enabled(device: Any | None) -> bool:
    return getattr(device, "alert_mode", "alert") != "log_only"


def new_ingest_key() -> str:
    return secrets.token_urlsafe(32)


def hash_ingest_key(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def ingest_key_matches(device: Any, presented_key: str | None) -> bool:
    stored = getattr(device, "ingest_key", None)
    if not stored or not presented_key:
        return False
    return secrets.compare_digest(stored, hash_ingest_key(presented_key))
