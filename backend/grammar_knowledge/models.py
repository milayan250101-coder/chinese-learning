from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer, String, Text,
    UniqueConstraint, Index,
)
from backend.database import Base


class GrammarCategory(Base):
    __tablename__ = "grammar_categories"

    id = Column(Integer, primary_key=True, index=True)
    teacher_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_id = Column(Integer, ForeignKey("grammar_categories.id", ondelete="SET NULL"), nullable=True, index=True)
    slug = Column(String(100), nullable=False)
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("teacher_user_id", "slug", name="uq_grammar_category_teacher_slug"),
        Index("ix_grammar_category_teacher_parent", "teacher_user_id", "parent_id"),
    )


class GrammarLevel(Base):
    __tablename__ = "grammar_levels"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), nullable=False, unique=True, index=True)
    name = Column(String(50), nullable=False)
    sort_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)


class GrammarKnowledgePoint(Base):
    __tablename__ = "grammar_knowledge_points"

    id = Column(Integer, primary_key=True, index=True)
    teacher_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("grammar_categories.id", ondelete="RESTRICT"), nullable=False, index=True)
    stable_key = Column(String(100), nullable=False)
    original_number = Column(Integer, nullable=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    canonical_name = Column(String(200), nullable=True)
    structure = Column(Text, nullable=True)
    explanation = Column(Text, nullable=True)
    usage_notes = Column(Text, nullable=True)
    teaching_objective = Column(Text, nullable=True)
    source_label = Column(String(255), nullable=True)
    status = Column(String(20), nullable=False, default="draft", index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("teacher_user_id", "stable_key", name="uq_grammar_point_teacher_key"),
        Index("ix_grammar_point_teacher_category", "teacher_user_id", "category_id"),
    )


class GrammarLevelMapping(Base):
    __tablename__ = "grammar_level_mappings"

    id = Column(Integer, primary_key=True, index=True)
    grammar_point_id = Column(Integer, ForeignKey("grammar_knowledge_points.id", ondelete="CASCADE"), nullable=False)
    level_id = Column(Integer, ForeignKey("grammar_levels.id", ondelete="RESTRICT"), nullable=False)
    level_role = Column(String(30), nullable=False, default="introduced")
    notes = Column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("grammar_point_id", "level_id", name="uq_grammar_point_level"),
    )


class GrammarExample(Base):
    __tablename__ = "grammar_examples"

    id = Column(Integer, primary_key=True, index=True)
    grammar_point_id = Column(Integer, ForeignKey("grammar_knowledge_points.id", ondelete="CASCADE"), nullable=False, index=True)
    chinese = Column(Text, nullable=False)
    pinyin = Column(Text, nullable=True)
    translations_json = Column(Text, nullable=True)
    teaching_note = Column(Text, nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
