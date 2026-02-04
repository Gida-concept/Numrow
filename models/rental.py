from __future__ import annotations
from typing import TYPE_CHECKING
from datetime import datetime

from sqlalchemy import ForeignKey, String, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import BaseModel

if TYPE_CHECKING:
    from .user import User
    from .number import Number
    from .payment import Payment

class Rental(BaseModel):
    """
    Represents a long-term rental of a phone number by a user.
    This table is for future use, to store more detailed rental info if needed.
    The primary flag `is_rent` is on the Number model itself.
    """
    __tablename__ = "rentals"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    number_id: Mapped[int] = mapped_column(ForeignKey("numbers.id"), nullable=False, unique=True, index=True)
    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False, index=True)
    active_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    auto_renew: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # --- Relationships ---
    # These relationships do not have back_populates to avoid circular dependencies
    user: Mapped["User"] = relationship("User")
    number: Mapped["Number"] = relationship("Number")
    payment: Mapped["Payment"] = relationship("Payment")

    def __repr__(self) -> str:
        return (
            f"<Rental(id={self.id}, user_id={self.user_id}, number_id={self.number_id}, "
            f"status='{self.status}', active_until='{self.active_until}')>"
        )
