from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    String,
)

from backend.database import Base


class LessonSession(Base):
    __tablename__ = "lesson_sessions"

    id = Column(Integer, primary_key=True, index=True)
    teacher_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False, index=True
    )
    student_id = Column(
        Integer, ForeignKey("students.id", ondelete="RESTRICT"),
        nullable=False, index=True
    )
    calendar_event_id = Column(
        Integer, ForeignKey("calendar_events.id", ondelete="SET NULL"),
        nullable=True, index=True
    )
    course_id = Column(String(20), nullable=True)
    started_at = Column(DateTime, nullable=False)
    ended_at = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=False, default="scheduled")
    completion_source = Column(String(30), nullable=True)
    teacher_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False,
        default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('scheduled', 'completed', 'cancelled', 'no_show')",
            name="ck_lesson_session_status"
        ),
        CheckConstraint(
            "completion_source IS NULL OR "
            "completion_source IN ('teacher', 'external_verified')",
            name="ck_lesson_session_completion_source"
        ),
        Index("ix_lesson_session_student_started",
              "student_id", "started_at"),
        Index("ix_lesson_session_teacher_started",
              "teacher_user_id", "started_at"),
    )
