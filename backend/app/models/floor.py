from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Floor(Base):
    __tablename__ = "floors"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    block_id: Mapped[int] = mapped_column(
        ForeignKey("blocks.id"),
        nullable=False,
        index=True,
    )

    floor_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
    )

    block = relationship(
        "Block",
        back_populates="floors",
    )

    devices = relationship(
        "Device",
        back_populates="floor",
    )