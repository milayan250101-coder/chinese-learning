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


class HSKGrammarPoint(Base):
    __tablename__ = "hsk_grammar_points"

    id = Column(Integer, primary_key=True, index=True)

    # HSK 级别：HSK 1、HSK 2……HSK 6
    level = Column(String(20), nullable=False, index=True)

    category = Column(String(100), nullable=False, default="")
    category_name = Column(String(100), nullable=False, default="")
    subcategory = Column(String(150), nullable=False, default="")
    content = Column(Text, nullable=False, default="")

    # 来源和版本信息
    syllabus_version = Column(String(20), nullable=False, default="2025")
    source_repo = Column(String(255), nullable=False)
    source_file = Column(String(255), nullable=False)
    source_url = Column(Text, nullable=False)

    # 原始文件中的条目序号，便于幂等更新
    source_index = Column(Integer, nullable=False)

    imported_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint(
            "syllabus_version",
            "level",
            "source_file",
            "source_index",
            name="uq_hsk_grammar_source_item",
        ),
        Index(
            "ix_hsk_grammar_level_category",
            "level",
            "category",
        ),
    )


class HSKVocabulary(Base):
    """2025 HSK 1–9 vocabulary."""

    __tablename__ = "hsk_vocabulary"

    id = Column(Integer, primary_key=True, index=True)

    # 原始词汇编号，保证重复导入时不产生重复记录
    number = Column(Integer, nullable=False, unique=True, index=True)

    # HSK 1–6 或 HSK 7–9
    level = Column(String(20), nullable=False, index=True)

    simplified = Column(String(100), nullable=False, index=True)
    traditional = Column(String(100), nullable=False)
    pinyin = Column(String(200), nullable=False, index=True)
    english = Column(Text, nullable=False)
    part_of_speech = Column(String(100), nullable=False, default="")

    syllabus_version = Column(String(20), nullable=False, default="2025")
    source_repo = Column(String(255), nullable=False)
    source_file = Column(String(255), nullable=False)

    dictionary_source = Column(String(255), nullable=False, default="CC-CEDICT")
    dictionary_license = Column(String(100), nullable=False, default="CC BY-SA 4.0")

    imported_at = Column(DateTime, nullable=False, default=datetime.utcnow)
