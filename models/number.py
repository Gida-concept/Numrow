from __future__ import annotations
from typing import TYPE_CHECKING
from datetime import datetime

from sqlalchemy import String, BigInteger, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import BaseModel

# This is a common pattern to avoid circular imports with type hints
if TYPE_CHECKING:
    from .user import User
    from .payment import Payment
    from .sms import Sms


class Number(BaseModel):
    """
    Represents a phone number purchased by a user for a specific service.
    """
    __tablename__ = "numbers"

    # The actual phone number string.
    phone_number: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True
    )

    # The unique ID for this activation from the external PVA service.
    # This is essential for polling SMS.
    pva_activation_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True
    )
    
    # The code for the service this number was purchased for (e.g., 'wa', 'tg').
    service_code: Mapped[str] = mapped_column(String(10), nullable=False)
    
    # The country code for the number (e.g., '0' for Nigeria).
    country_code: Mapped[str] = mapped_column(String(10), nullable=False)

    # The status of the number activation ('active', 'expired', 'finished', 'banned').
    status: Mapped[str] = mapped_column(
        String(50),
        default="active",
        nullable=False,
        index=True
    )

    # The timestamp when this number activation expires.
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # --- Foreign Keys and Relationships ---
    
    # Link to the user who owns this number.
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    user: Mapped["User"] = relationship(back_populates="numbers")
    
    # Link to the payment that funded this number purchase.
    payment_id: Mapped[int] = mapped_column(
        ForeignKey("payments.id", ondelete="CASCADE"),
        unique=True, # A payment can only purchase one number
        nullable=False
    )
    payment: Mapped["Payment"] = relationship(back_populates="number")
    
    # A number can have many SMS messages.
    sms_messages: Mapped[list["Sms"]] = relationship(
        "Sms",
        back_populates="number",
        cascade="all, delete-orphan"
    )
    
    # A number can be part of one rental agreement.
    rental: Mapped[list["Rental"]] = relationship(back_populates="number")

    def __repr__(self) -> str:
        return (
            f"<Number(id={self.id}, phone_number='{self.phone_number}', "
            f"status='{self.status}', pva_activation_id='{self.pva_activation_id}')>"
        )

# --- Add reverse relationships AFTER all models are defined in their own files ---
# We need to import the related models here to add the relationships.
from .user import User
from .payment import Payment
from .rental import Rental

# Add the reverse relationship to User and Payment models for type hinting
User.numbers = relationship("Number", back_populates="user", cascade="all, delete-orphan")
Payment.number = relationship("Number", back_populates="payment", uselist=False)
