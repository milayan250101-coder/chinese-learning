from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    Index,
)

from backend.database import Base


class StudentAuthAccount(Base):
    """独立学生登录账号，与现有 Student 资料一对一关联。"""

    __tablename__ = "student_auth_accounts"

    id = Column(Integer, primary_key=True, index=True)

    student_id = Column(
        Integer,
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    login_username = Column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
    )

    hashed_password = Column(String(255), nullable=False)

    is_active = Column(Boolean, nullable=False, default=True)

    must_change_password = Column(
        Boolean,
        nullable=False,
        default=True,
    )

    last_login_at = Column(DateTime, nullable=True)

    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    __table_args__ = (
        UniqueConstraint(
            "student_id",
            name="uq_student_auth_account_student",
        ),
        Index(
            "ix_student_auth_account_active",
            "is_active",
        ),
    )
