from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    Float,
    UniqueConstraint,
)

from backend.database import Base


class Topic(Base):
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    category = Column(String(100), nullable=True, index=True)
    description = Column(Text, nullable=True)
    difficulty = Column(String(50), nullable=True)
    hsk_level = Column(String(50), nullable=True)

    source_type = Column(String(30), nullable=False, default="ai")
    status = Column(String(30), nullable=False, default="pending", index=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )


class LessonTopic(Base):
    __tablename__ = "lesson_topics"

    id = Column(Integer, primary_key=True, index=True)
    lesson_plan_id = Column(
        Integer,
        ForeignKey("lesson_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    topic_id = Column(
        Integer,
        ForeignKey("topics.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    relevance = Column(Float, nullable=True)
    extracted_by = Column(String(30), default="ai")

    __table_args__ = (
        UniqueConstraint(
            "lesson_plan_id",
            "topic_id",
            name="uq_lesson_topic"
        ),
    )


class TopicVocabulary(Base):
    __tablename__ = "topic_vocabulary"

    id = Column(Integer, primary_key=True, index=True)
    topic_id = Column(
        Integer,
        ForeignKey("topics.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    chinese = Column(String(255), nullable=False)
    pinyin = Column(String(255), nullable=True)
    translation = Column(Text, nullable=True)
    part_of_speech = Column(String(100), nullable=True)
    hsk_level = Column(String(50), nullable=True)

    example_sentence = Column(Text, nullable=True)
    example_pinyin = Column(Text, nullable=True)
    example_translation = Column(Text, nullable=True)

    source_lesson_id = Column(
        Integer,
        ForeignKey("lesson_plans.id", ondelete="SET NULL"),
        nullable=True
    )

    status = Column(String(30), nullable=False, default="pending", index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class TopicExample(Base):
    __tablename__ = "topic_examples"

    id = Column(Integer, primary_key=True, index=True)
    topic_id = Column(
        Integer,
        ForeignKey("topics.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    chinese = Column(Text, nullable=False)
    pinyin = Column(Text, nullable=True)
    translation = Column(Text, nullable=True)
    difficulty = Column(String(50), nullable=True)

    source_lesson_id = Column(
        Integer,
        ForeignKey("lesson_plans.id", ondelete="SET NULL"),
        nullable=True
    )

    status = Column(String(30), nullable=False, default="pending", index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
