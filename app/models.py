from datetime import datetime

from sqlalchemy import JSON, DateTime, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    # В тестах используется SQLite, где нет ARRAY, поэтому там рубрики хранятся как JSON.
    rubrics: Mapped[list[str]] = mapped_column(ARRAY(String).with_variant(JSON, "sqlite"))
    text: Mapped[str] = mapped_column(Text)
    created_date: Mapped[datetime] = mapped_column(DateTime, index=True)
