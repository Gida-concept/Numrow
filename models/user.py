from __future__ import annotations
from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import BaseModel
# We do NOT import Payment, Number, or Rental here to avoid cycles. 
# We use string references instead.

class User(BaseModel):
    """
    Represents a user of the Telegram bot.
    """
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        nullable=False,
        index=True,
        comment="The user's unique Telegram ID"
    )

    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=True,
        comment="User's full name from Telegram"
    )

    username: Mapped[str] = mapped_column(
        String(100),
        nullable=True,
        comment="User's Telegram username"
    )

    language_code: Mapped[str] = mapped_column(
        String(5),
        default='en',
        nullable=False,
        comment="User's preferred language code"
    )

    # --- Relationships ---
    # Defined explicitly with string references
    payments: Mapped[list["Payment"]] = relationship(
        "Payment",
        back_populates="user",
        lazy="selectin"
    )

    numbers: Mapped[list["Number"]] = relationship(
        "Number", 
        back_populates="user", 
        cascade="all, delete-orphan"
    )

    rentals: Mapped[list["Rental"]] = relationship(
        "Rental", 
        back_populates="user", 
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, username='{self.username}')>"
