from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    device_id: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    # Physical location
    floor_id: Mapped[int | None] = mapped_column(
        ForeignKey("floors.id"),
        nullable=True,
        index=True,
    )

    location: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    firmware_version: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    ingest_key: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True,
    )

    floor = relationship(
        "Floor",
        back_populates="devices",
    )

    telemetry = relationship(
        "Telemetry",
        back_populates="device",
    )

    relays = relationship(
        "Relay",
        back_populates="device",
    )

    # Relationship to Faults
    faults = relationship(
        "Fault",
        back_populates="device",
    )