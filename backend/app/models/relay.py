from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Relay(Base):
    __tablename__ = "relays"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    device_id: Mapped[int] = mapped_column(
        ForeignKey("devices.id"),
        nullable=False,
        index=True,
    )

    relay_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    gpio_pin: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    commanded_state: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    actual_state: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
    )

    is_on: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    device = relationship(
        "Device",
        back_populates="relays",
    )