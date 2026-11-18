from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey,
    UniqueConstraint, CheckConstraint, Index
)

from backend.database import Base


class HSKCourseKnowledgeLink(Base):
    __tablename__ = "hsk_course_knowledge_links"

    id = Column(Integer, primary_key=True, index=True)

    teacher_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    knowledge_type = Column(String(20), nullable=False)
    vocabulary_number = Column(
        Integer,
        ForeignKey("hsk_vocabulary.number", ondelete="CASCADE"),
        nullable=True,
    )
    grammar_point_id = Column(
        Integer,
        ForeignKey("hsk_grammar_points.id", ondelete="CASCADE"),
        nullable=True,
    )

    # 用统一字符串键实现可靠的跨类型去重
    # 示例：vocabulary:123 / grammar:456
    knowledge_key = Column(String(100), nullable=False)

    course_series = Column(String(10), nullable=False)
    course_id = Column(String(30), nullable=False)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint(
            """
            (knowledge_type = 'vocabulary'
                AND vocabulary_number IS NOT NULL
                AND grammar_point_id IS NULL)
            OR
            (knowledge_type = 'grammar'
                AND grammar_point_id IS NOT NULL
                AND vocabulary_number IS NULL)
            """,
            name="ck_hsk_course_link_target",
        ),
        CheckConstraint(
            "course_series IN ('CL')",
            name="ck_hsk_course_link_series",
        ),
        UniqueConstraint(
            "teacher_user_id",
            "knowledge_key",
            "course_series",
            "course_id",
            name="uq_hsk_knowledge_course_teacher",
        ),
        Index("ix_hsk_course_link_knowledge", "knowledge_key"),
    )


class StudentKnowledgeManualEntry(Base):
    __tablename__ = "student_knowledge_manual_entries"

    id = Column(Integer, primary_key=True, index=True)

    student_id = Column(
        Integer,
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
    )
    teacher_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    knowledge_type = Column(String(20), nullable=False)
    vocabulary_number = Column(
        Integer,
        ForeignKey("hsk_vocabulary.number", ondelete="CASCADE"),
        nullable=True,
    )
    grammar_point_id = Column(
        Integer,
        ForeignKey("hsk_grammar_points.id", ondelete="CASCADE"),
        nullable=True,
    )

    knowledge_key = Column(String(100), nullable=False)
    syllabus_version = Column(String(20), nullable=False, default="2025")

    source_type = Column(
        String(40),
        nullable=False,
        default="teacher_manual",
    )
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint(
            """
            (knowledge_type = 'vocabulary'
                AND vocabulary_number IS NOT NULL
                AND grammar_point_id IS NULL)
            OR
            (knowledge_type = 'grammar'
                AND grammar_point_id IS NOT NULL
                AND vocabulary_number IS NULL)
            """,
            name="ck_student_manual_entry_target",
        ),
        UniqueConstraint(
            "student_id",
            "knowledge_key",
            "source_type",
            name="uq_student_manual_knowledge_source",
        ),
        Index("ix_student_manual_entry_student", "student_id"),
    )
