from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    CheckConstraint,
    Index,
)

from backend.database import Base


def utcnow():
    return datetime.utcnow()


class GrammarCategory(Base):
    """教师语法知识库的可扩展分类，支持多级目录。"""

    __tablename__ = "grammar_categories"

    id = Column(Integer, primary_key=True, index=True)
    parent_id = Column(
        Integer,
        ForeignKey("grammar_categories.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    owner_teacher_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)


class GrammarKnowledgePoint(Base):
    """教师维护的统一语法知识点主记录。"""

    __tablename__ = "grammar_knowledge_points"

    id = Column(Integer, primary_key=True, index=True)

    teacher_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    primary_category_id = Column(
        Integer,
        ForeignKey("grammar_categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # 保留原始93项目录的编号和文字，不覆盖原文
    source_item_no = Column(Integer, nullable=True, index=True)
    original_name = Column(Text, nullable=True)

    # 教师维护的标准名称和说明
    title = Column(String(255), nullable=False)
    normalized_name = Column(String(255), nullable=True, index=True)
    description = Column(Text, nullable=True)
    teaching_objective = Column(Text, nullable=True)

    status = Column(String(30), nullable=False, default="draft", index=True)
    sort_order = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'published', 'archived')",
            name="ck_grammar_point_status",
        ),
        Index(
            "ix_grammar_point_teacher_status",
            "teacher_user_id",
            "status",
        ),
    )


class GrammarPointCategory(Base):
    """知识点与分类的关联，允许一个知识点归入多个分类。"""

    __tablename__ = "grammar_point_categories"

    id = Column(Integer, primary_key=True, index=True)
    grammar_point_id = Column(
        Integer,
        ForeignKey("grammar_knowledge_points.id", ondelete="CASCADE"),
        nullable=False,
    )
    category_id = Column(
        Integer,
        ForeignKey("grammar_categories.id", ondelete="CASCADE"),
        nullable=False,
    )
    is_primary = Column(Integer, nullable=False, default=0)

    __table_args__ = (
        UniqueConstraint(
            "grammar_point_id",
            "category_id",
            name="uq_grammar_point_category",
        ),
    )


class GrammarPointLevel(Base):
    """知识点与HSK等级的多对多关联。"""

    __tablename__ = "grammar_point_levels"

    id = Column(Integer, primary_key=True, index=True)
    grammar_point_id = Column(
        Integer,
        ForeignKey("grammar_knowledge_points.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    level_code = Column(String(20), nullable=False, index=True)
    mapping_type = Column(String(30), nullable=False, default="introduced")

    __table_args__ = (
        UniqueConstraint(
            "grammar_point_id",
            "level_code",
            name="uq_grammar_point_level",
        ),
        CheckConstraint(
            "mapping_type IN ('introduced', 'review', 'extension')",
            name="ck_grammar_point_level_mapping_type",
        ),
    )


class GrammarRule(Base):
    """一个知识点可以包含多条规则或语法公式。"""

    __tablename__ = "grammar_rules"

    id = Column(Integer, primary_key=True, index=True)
    grammar_point_id = Column(
        Integer,
        ForeignKey("grammar_knowledge_points.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rule_type = Column(String(50), nullable=False, default="general")
    formula = Column(Text, nullable=True)
    explanation = Column(Text, nullable=False)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)


class GrammarExample(Base):
    """语法例句，支持拼音和多语言翻译。"""

    __tablename__ = "grammar_examples"

    id = Column(Integer, primary_key=True, index=True)
    grammar_point_id = Column(
        Integer,
        ForeignKey("grammar_knowledge_points.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chinese_text = Column(Text, nullable=False)
    pinyin = Column(Text, nullable=True)
    translations_json = Column(Text, nullable=True)
    explanation = Column(Text, nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=utcnow)


class GrammarPitfall(Base):
    """易错点及纠正说明。"""

    __tablename__ = "grammar_pitfalls"

    id = Column(Integer, primary_key=True, index=True)
    grammar_point_id = Column(
        Integer,
        ForeignKey("grammar_knowledge_points.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = Column(String(255), nullable=True)
    incorrect_example = Column(Text, nullable=True)
    correct_example = Column(Text, nullable=True)
    explanation = Column(Text, nullable=False)
    sort_order = Column(Integer, nullable=False, default=0)


class GrammarPointRelation(Base):
    """语法知识点之间的关联，例如相似、对比、前置知识。"""

    __tablename__ = "grammar_point_relations"

    id = Column(Integer, primary_key=True, index=True)
    source_point_id = Column(
        Integer,
        ForeignKey("grammar_knowledge_points.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_point_id = Column(
        Integer,
        ForeignKey("grammar_knowledge_points.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    relation_type = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "source_point_id",
            "target_point_id",
            "relation_type",
            name="uq_grammar_point_relation",
        ),
        CheckConstraint(
            "source_point_id != target_point_id",
            name="ck_grammar_point_relation_not_self",
        ),
    )


class GrammarSourceLink(Base):
    """将教师知识点关联到已有的HSK导入语法条目，不复制旧数据。"""

    __tablename__ = "grammar_source_links"

    id = Column(Integer, primary_key=True, index=True)
    grammar_point_id = Column(
        Integer,
        ForeignKey("grammar_knowledge_points.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    hsk_grammar_point_id = Column(
        Integer,
        ForeignKey("hsk_grammar_points.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    created_at = Column(DateTime, nullable=False, default=utcnow)

    __table_args__ = (
        UniqueConstraint(
            "grammar_point_id",
            "hsk_grammar_point_id",
            name="uq_grammar_source_link",
        ),
    )


class GrammarMaterialLink(Base):
    """将语法知识点关联到现有教学计划资料。"""

    __tablename__ = "grammar_material_links"

    id = Column(Integer, primary_key=True, index=True)
    grammar_point_id = Column(
        Integer,
        ForeignKey("grammar_knowledge_points.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    lesson_plan_id = Column(
        Integer,
        ForeignKey("lesson_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)

    __table_args__ = (
        UniqueConstraint(
            "grammar_point_id",
            "lesson_plan_id",
            name="uq_grammar_material_link",
        ),
    )
