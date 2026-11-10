from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Index,
)

from backend.database import Base


class HSKHanzi(Base):
    """HSK 2025 Hanzi reference list."""

    __tablename__ = "hsk_hanzi"

    id = Column(Integer, primary_key=True, index=True)

    character = Column(String(10), nullable=False, index=True)
    level = Column(String(20), nullable=False, index=True)

    syllabus_version = Column(String(20), nullable=False, default="2025")

    source_repo = Column(String(255), nullable=False)
    source_file = Column(String(255), nullable=False)
    source_url = Column(Text, nullable=False)

    imported_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint(
            "syllabus_version",
            "level",
            "character",
            name="uq_hsk_hanzi_version_level_character",
        ),
        Index(
            "ix_hsk_hanzi_level_character",
            "level",
            "character",
        ),
    )
