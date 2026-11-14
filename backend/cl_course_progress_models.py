from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy import ForeignKey, UniqueConstraint, Index

from backend.database import Base


class CLCourseProgress(Base):
    __tablename__ = "cl_course_progress"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(
        Integer,
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
    )
    course_id = Column(String(20), nullable=False)
    learned = Column(Boolean, nullable=False, default=False)
    learned_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    __table_args__ = (
        UniqueConstraint(
            "student_id",
            "course_id",
            name="uq_cl_course_progress_student_course",
        ),
        Index("ix_cl_course_progress_student", "student_id"),
    )
