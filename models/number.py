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
    from .rental import Rental


class Number(BaseModel):
    """
    Represents a phone number purchased by a user, for either temporary or rental use.
    """
    __tablename__ = "numbers"

    phone_number: Mapped[str] = mapped_column(String(30), nullable=False, index=True)

    # The unique ID for this activation from the external PVA service.
    pva_activation_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    
    # The code for the service this number was purchased for (e.g., '4031').
    service_code: Mapped[str] = mapped_column(String(20), nullable=False)
    
    # The country code for the number (e.g., '58' for USA).
    country_code: Mapped[str] = mapped_column(String(10), nullable=False)

    # The status of the number activation ('active', 'expired', 'finished', 'banned').
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False, index=True)

    # --- NEW COLUMNS ---
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
    # --- END NEW COLUMNS ---

    # The timestamp when this number activation expires.
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # --- Foreign Keys and Relationships ---
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id", ondelete="CASCADE"), unique=True, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="numbers")
    payment: Mapped["Payment"] = relationship("Payment", back_populates="number")
    
    sms_messages: Mapped[list["Sms"]] = relationship(
        "Sms",
        back_populates="number",
        cascade="all, delete-orphan"
    )
    
    # The relationship to the Rental model is now obsolete as we store the flag here.
    # We can remove it or keep it if you plan to store more rental-specific data there.
    # For now, let's keep the rental table for future use but rely on the `is_rent` flag.
    rental: Mapped["Rental"] = relationship("Rental", back_populates="number")

    def __repr__(self) -> str:
        return (
            f"<Number(id={self.id}, phone_number='{self.phone_number}', "
            f"status='{self.status}', is_rent={self.is_rent})>"
        )
