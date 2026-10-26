from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Block(Base):
    __tablename__ = "blocks"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    college_id: Mapped[int] = mapped_column(
        ForeignKey("colleges.id"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    code: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    description: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
    )

    college = relationship(
        "College",
        back_populates="blocks",
    )

    floors = relationship(
        "Floor",
        back_populates="block",
        cascade="all, delete-orphan",
    )