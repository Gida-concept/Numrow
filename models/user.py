from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import BaseModel


class User(BaseModel):
    """
    Represents a user of the Telegram bot.
    """
    __tablename__ = "users"

    # Telegram's user ID can be a large number, so BigInteger is safer than Integer.
    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        nullable=False,
        index=True,
        comment="The user's unique Telegram ID"
    )

    # User's full name from Telegram.
    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=True,
        comment="User's full name from Telegram"
    )

    # User's Telegram username (e.g., @username), can be optional.
    username: Mapped[str] = mapped_column(
        String(100),
        nullable=True,
        comment="User's Telegram username"
    )

    # The language code (e.g., 'en', 'fr') for i18n.
    language_code: Mapped[str] = mapped_column(
        String(5),
        default='en',
        nullable=False,
        comment="User's preferred language code"
    )

    # --- Relationships ---
    # This creates a link to the Payment model.
    # 'back_populates' creates a two-way relationship, so from a Payment object,
    # you can access the user via `payment.user`.
    # 'lazy="selectin"' is an efficient loading strategy.
    payments: Mapped[list["Payment"]] = relationship(
        "Payment",
        back_populates="user",
        lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, username='{self.username}')>"