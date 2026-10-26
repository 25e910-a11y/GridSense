from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(30), nullable=False, default="operator")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    assigned_block_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("blocks.id"), nullable=True)
    assigned_floor_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("floors.id"), nullable=True)

    block = relationship("Block", foreign_keys=[assigned_block_id])
    floor = relationship("Floor", foreign_keys=[assigned_floor_id])
