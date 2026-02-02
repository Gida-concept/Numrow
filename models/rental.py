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
    """
    __tablename__ = "rentals"

    # Foreign key to the user who is renting the number.
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    # Foreign key to the number being rented.
    number_id: Mapped[int] = mapped_column(ForeignKey("numbers.id"), nullable=False, unique=True, index=True)

    # Foreign key to the most recent payment that funded or renewed this rental.
    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id"), nullable=False, index=True)

    # Status of the rental subscription. e.g., 'active', 'expired', 'cancelled'.
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False, index=True)

    # The timestamp until which the rental is paid and active.
    active_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Flag to indicate if the user wants the rental to auto-renew.
    auto_renew: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


    # --- Relationships ---
    # We use string references ("User", "Number") to avoid circular imports.
    user: Mapped["User"] = relationship("User", back_populates="rentals")
    number: Mapped["Number"] = relationship("Number", back_populates="rental")
    payment: Mapped["Payment"] = relationship("Payment")

    def __repr__(self) -> str:
        return (
            f"<Rental(id={self.id}, user_id={self.user_id}, number_id={self.number_id}, "
            f"status='{self.status}', active_until='{self.active_until}')>"
        )
