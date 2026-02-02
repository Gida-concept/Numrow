from __future__ import annotations
from typing import TYPE_CHECKING

from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import BaseModel

if TYPE_CHECKING:
    from .number import Number


class Sms(BaseModel):
    """
    Represents a single SMS message received for a purchased number.
    """
    __tablename__ = "sms"

    # Foreign key to the number that received this SMS.
    number_id: Mapped[int] = mapped_column(
        ForeignKey("numbers.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # The unique message ID from the external PVA service.
    # This helps prevent processing the same message twice.
    pva_sms_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True
    )

    # The full text content of the SMS message.
    full_text: Mapped[str] = mapped_column(Text, nullable=False)

    # The extracted verification code, if any.
    verification_code: Mapped[str] = mapped_column(String(50), nullable=True)

    # --- Relationships ---

    # Link back to the Number object.
    number: Mapped["Number"] = relationship("Number", back_populates="sms_messages")

    def __repr__(self) -> str:
        return (
            f"<Sms(id={self.id}, number_id={self.number_id}, "
            f"code='{self.verification_code}')>"
        )