from __future__ import annotations
from typing import TYPE_CHECKING
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import BaseModel

if TYPE_CHECKING:
    from .user import User
    from .payment import Payment
    from .sms import Sms
    from .rental import Rental


class Number(BaseModel):
    """
    Represents a phone number purchased by a user.
    """
    __tablename__ = "numbers"

    phone_number: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    pva_activation_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    service_code: Mapped[str] = mapped_column(String(10), nullable=False)
    country_code: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # --- Foreign Keys ---
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id", ondelete="CASCADE"), unique=True, nullable=False)

    # --- Relationships ---
    user: Mapped["User"] = relationship("User", back_populates="numbers")
    payment: Mapped["Payment"] = relationship("Payment", back_populates="number")
    
    sms_messages: Mapped[list["Sms"]] = relationship(
        "Sms",
        back_populates="number",
        cascade="all, delete-orphan"
    )
    
    rental: Mapped["Rental"] = relationship("Rental", back_populates="number")

    def __repr__(self) -> str:
        return (
            f"<Number(id={self.id}, phone_number='{self.phone_number}', "
            f"status='{self.status}', pva_activation_id='{self.pva_activation_id}')>"
        )
