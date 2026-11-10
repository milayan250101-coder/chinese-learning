from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime

from backend.database import Base


class ESLTopicCatalog(Base):
    __tablename__ = "esl_catalog_topics"

    id = Column(Integer, primary_key=True, index=True)

    # 英文原始话题名称
    title_en = Column(String(255), nullable=False, index=True)

    # A-Z 字母；Grammar 和 Idioms 使用 NULL
    letter = Column(String(1), nullable=True, index=True)

    # alphabetical / grammar / idioms
    category = Column(String(30), nullable=False, index=True)

    # 原网站链接：唯一标识一条目录记录
    source_url = Column(String(1000), nullable=False, unique=True, index=True)

    # 中文译名和拼音，后续分批生成
    title_zh = Column(String(255), nullable=True, index=True)
    pinyin = Column(String(255), nullable=True)

    # pending / translated / error
    translation_status = Column(
        String(30),
        nullable=False,
        default="pending",
        index=True
    )

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
