from datetime import datetime

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Telemetry(Base):
    __tablename__ = "telemetry"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    # Device relationship
    device_id: Mapped[int] = mapped_column(
        ForeignKey("devices.id"),
        nullable=False,
        index=True,
    )

    # Phase / PZEM identification
    phase: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    # Electrical measurements
    voltage: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    current: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    power: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    energy: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    power_factor: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    frequency: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    # Environmental measurement
    temperature: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    # Time information
    sampled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    # Actual sampling interval used by the device
    sampling_interval_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # Why this record was transmitted
    transmission_reason: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    # Where the data came from
    source: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    # Basic quality indicator
    data_quality: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    # Relationship to Device
    device = relationship(
        "Device",
        back_populates="telemetry",
    )