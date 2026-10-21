
from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column

from database.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    nivel: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="pendente"
    )

    session_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )
