from __future__ import annotations
from typing import TYPE_CHECKING
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import BaseModel

if TYPE_CHECKING:
    from .user import User
    from .payment import Payment
    from .sms import Sms
    # Remove the self-import and the Rental import to break the loop
    # from .number import Number
    # from .rental import Rental

class Number(BaseModel):
    """
    Represents a phone number purchased by a user, for either temporary or rental use.
    """
    __tablename__ = "numbers"

    phone_number: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    pva_activation_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    service_code: Mapped[str] = mapped_column(String(20), nullable=False)
    country_code: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False, index=True)

    is_rent: Mapped[bool] = mapped_column(
        Boolean, 
        default=False, 
        nullable=False,
        index=True,
        comment="True if this is a long-term rental, False if temporary."
    )
    renewal_notice_sent: Mapped[bool] = mapped_column(
        Boolean, 
        default=False, 
        nullable=False,
        comment="True if a renewal warning has been sent for a rental number."
    )

    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id", ondelete="CASCADE"), unique=True, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="numbers")
    payment: Mapped["Payment"] = relationship("Payment", back_populates="number")
    
    sms_messages: Mapped[list["Sms"]] = relationship(
        "Sms",
        back_populates="number",
        cascade="all, delete-orphan"
    )
    
    # This line was causing the circular import. We remove it.
    # rental: Mapped["Rental"] = relationship("Rental", back_populates="number")

    def __repr__(self) -> str:
        return (
            f"<Number(id={self.id}, phone_number='{self.phone_number}', "
            f"status='{self.status}', is_rent={self.is_rent})>"
        )
