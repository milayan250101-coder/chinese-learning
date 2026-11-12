from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey,
    UniqueConstraint, CheckConstraint, Index
)

from backend.database import Base


def utcnow():
    return datetime.utcnow()


class CoreVocabulary(Base):
    """教师维护的统一核心词汇主档。"""

    __tablename__ = "core_vocabularies"

    id = Column(Integer, primary_key=True, index=True)
    teacher_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False, index=True
    )
    simplified = Column(String(100), nullable=False, index=True)
    traditional = Column(String(100), nullable=True)
    pinyin = Column(String(200), nullable=False, index=True)
    part_of_speech = Column(String(100), nullable=False, default="未标注")
    definition = Column(Text, nullable=True)
    translations_json = Column(Text, nullable=True)
    teaching_notes = Column(Text, nullable=True)
    status = Column(String(30), nullable=False, default="draft", index=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    __table_args__ = (
        UniqueConstraint(
            "teacher_user_id", "simplified", "pinyin", "part_of_speech",
            name="uq_core_vocab_teacher_word"
        ),
        CheckConstraint(
            "status IN ('draft', 'published', 'archived')",
            name="ck_core_vocab_status"
        ),
    )


class CoreVocabularyHSKLink(Base):
    """核心词汇与现有HSK词条的关联，不复制HSK原始数据。"""

    __tablename__ = "core_vocabulary_hsk_links"

    id = Column(Integer, primary_key=True, index=True)
    core_vocabulary_id = Column(
        Integer, ForeignKey("core_vocabularies.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    hsk_vocabulary_id = Column(
        Integer, ForeignKey("hsk_vocabulary.id", ondelete="RESTRICT"),
        nullable=False, index=True
    )
    mapping_type = Column(String(30), nullable=False, default="introduced")

    __table_args__ = (
        UniqueConstraint(
            "core_vocabulary_id", "hsk_vocabulary_id",
            name="uq_core_vocab_hsk_link"
        ),
        CheckConstraint(
            "mapping_type IN ('introduced', 'review', 'extension')",
            name="ck_core_vocab_hsk_mapping"
        ),
    )


class CoreVocabularyGrammarLink(Base):
    """核心词汇与教师语法知识点之间的关联。"""

    __tablename__ = "core_vocabulary_grammar_links"

    id = Column(Integer, primary_key=True, index=True)
    core_vocabulary_id = Column(
        Integer, ForeignKey("core_vocabularies.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    grammar_point_id = Column(
        Integer, ForeignKey("grammar_knowledge_points.id", ondelete="RESTRICT"),
        nullable=False, index=True
    )
    relation_type = Column(String(30), nullable=False, default="uses")
    description = Column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "core_vocabulary_id", "grammar_point_id", "relation_type",
            name="uq_core_vocab_grammar_link"
        ),
    )


class MasterCourseLevel(Base):
    """教师自己的Master课程等级。"""

    __tablename__ = "master_course_levels"

    id = Column(Integer, primary_key=True, index=True)
    teacher_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False, index=True
    )
    level_code = Column(String(30), nullable=False)
    title = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, nullable=False, default=utcnow)

    __table_args__ = (
        UniqueConstraint(
            "teacher_user_id", "level_code",
            name="uq_master_level_teacher_code"
        ),
    )


class MasterCourseUnit(Base):
    """Master等级下面的教学单元，支持父子层级。"""

    __tablename__ = "master_course_units"

    id = Column(Integer, primary_key=True, index=True)
    teacher_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False, index=True
    )
    level_id = Column(
        Integer, ForeignKey("master_course_levels.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    parent_unit_id = Column(
        Integer, ForeignKey("master_course_units.id", ondelete="RESTRICT"),
        nullable=True, index=True
    )
    unit_code = Column(String(50), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    teaching_objective = Column(Text, nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)
    status = Column(String(30), nullable=False, default="draft")
    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    __table_args__ = (
        UniqueConstraint("level_id", "unit_code", name="uq_master_unit_code"),
        CheckConstraint(
            "status IN ('draft', 'published', 'archived')",
            name="ck_master_unit_status"
        ),
    )


class MasterUnitVocabulary(Base):
    """教学单元与核心词汇的关联。"""

    __tablename__ = "master_unit_vocabularies"

    id = Column(Integer, primary_key=True, index=True)
    unit_id = Column(
        Integer, ForeignKey("master_course_units.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    core_vocabulary_id = Column(
        Integer, ForeignKey("core_vocabularies.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    relation_type = Column(String(30), nullable=False, default="core")
    sort_order = Column(Integer, nullable=False, default=0)

    __table_args__ = (
        UniqueConstraint(
            "unit_id", "core_vocabulary_id",
            name="uq_master_unit_vocabulary"
        ),
        CheckConstraint(
            "relation_type IN ('core', 'support', 'extension')",
            name="ck_master_unit_vocab_type"
        ),
    )


class MasterUnitGrammarPoint(Base):
    """教学单元与语法知识点的关联。"""

    __tablename__ = "master_unit_grammar_points"

    id = Column(Integer, primary_key=True, index=True)
    unit_id = Column(
        Integer, ForeignKey("master_course_units.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    grammar_point_id = Column(
        Integer, ForeignKey("grammar_knowledge_points.id", ondelete="RESTRICT"),
        nullable=False, index=True
    )
    relation_type = Column(String(30), nullable=False, default="core")
    sort_order = Column(Integer, nullable=False, default=0)

    __table_args__ = (
        UniqueConstraint(
            "unit_id", "grammar_point_id",
            name="uq_master_unit_grammar"
        ),
    )


class TeachingScenario(Base):
    """教师维护的生活、职场和行业实战场景。"""

    __tablename__ = "teaching_scenarios"

    id = Column(Integer, primary_key=True, index=True)
    teacher_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False, index=True
    )
    name = Column(String(200), nullable=False)
    domain = Column(String(100), nullable=False, default="日常生活")
    description = Column(Text, nullable=True)
    target_tasks = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)

    __table_args__ = (
        UniqueConstraint(
            "teacher_user_id", "name", "domain",
            name="uq_teaching_scenario_teacher_name"
        ),
    )


class MasterUnitScenario(Base):
    """教学单元与实战场景的关联。"""

    __tablename__ = "master_unit_scenarios"

    id = Column(Integer, primary_key=True, index=True)
    unit_id = Column(
        Integer, ForeignKey("master_course_units.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    scenario_id = Column(
        Integer, ForeignKey("teaching_scenarios.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    sort_order = Column(Integer, nullable=False, default=0)

    __table_args__ = (
        UniqueConstraint(
            "unit_id", "scenario_id",
            name="uq_master_unit_scenario"
        ),
    )
