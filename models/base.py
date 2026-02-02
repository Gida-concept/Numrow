from sqlalchemy import Column, Integer, DateTime
from sqlalchemy.orm import declarative_base, Mapped, mapped_column
from sqlalchemy.sql import func

# declarative_base() returns a new base class from which all mapped classes should inherit.
# This object is the registry for all our table models.
Base = declarative_base()


class BaseModel(Base):
    """
    An abstract base model that provides common fields for all other models.

    This includes an auto-incrementing primary key 'id' and
    'created_at' / 'updated_at' timestamps that are automatically managed
    by the database.

    By inheriting from this, our other models (User, Payment, etc.) will
    automatically get these columns.
    """
    __abstract__ = True  # This tells SQLAlchemy not to create a table for BaseModel itself.

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="The time the record was created (UTC)"
    )

    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="The time the record was last updated (UTC)"
    )