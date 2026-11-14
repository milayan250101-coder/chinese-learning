from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)

from backend.database import Base


class CalendarConnection(Base):
    __tablename__ = "calendar_connections"

    id = Column(Integer, primary_key=True, index=True)
    teacher_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    provider = Column(String(30), nullable=False)
    account_name = Column(String(255), nullable=True)
    external_account_id = Column(String(255), nullable=True)
    connection_status = Column(String(30), nullable=False, default="pending")
    sync_capability = Column(String(30), nullable=False, default="unsupported")
    sync_enabled = Column(Boolean, nullable=False, default=False)
    credential_data_encrypted = Column(Text, nullable=True)
    token_expires_at = Column(DateTime, nullable=True)
    last_synced_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False,
        default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        UniqueConstraint(
            "teacher_user_id", "provider", "external_account_id",
            name="uq_calendar_connection_account"
        ),
        CheckConstraint(
            "sync_capability IN "
            "('bidirectional', 'import_only', 'export_only', 'unsupported')",
            name="ck_calendar_connection_capability"
        ),
        Index("ix_calendar_connection_teacher_provider",
              "teacher_user_id", "provider"),
    )


class CalendarExternalCalendar(Base):
    __tablename__ = "calendar_external_calendars"

    id = Column(Integer, primary_key=True, index=True)
    connection_id = Column(
        Integer, ForeignKey("calendar_connections.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    external_calendar_id = Column(String(500), nullable=False)
    calendar_name = Column(String(255), nullable=True)
    is_selected = Column(Boolean, nullable=False, default=True)
    sync_direction = Column(String(20), nullable=False, default="both")
    last_sync_token = Column(Text, nullable=True)
    last_synced_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False,
        default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        UniqueConstraint(
            "connection_id", "external_calendar_id",
            name="uq_external_calendar_identity"
        ),
        CheckConstraint(
            "sync_direction IN ('both', 'inbound', 'outbound', 'none')",
            name="ck_external_calendar_direction"
        ),
    )


class CalendarEvent(Base):
    __tablename__ = "calendar_events"

    id = Column(Integer, primary_key=True, index=True)
    teacher_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    student_id = Column(
        Integer, ForeignKey("students.id", ondelete="RESTRICT"),
        nullable=True, index=True
    )
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    event_type = Column(String(30), nullable=False, default="lesson")
    start_at = Column(DateTime, nullable=False)
    end_at = Column(DateTime, nullable=False)
    timezone = Column(String(100), nullable=False, default="UTC")
    status = Column(String(30), nullable=False, default="scheduled")
    location = Column(String(500), nullable=True)
    recurrence_rule = Column(Text, nullable=True)
    created_by = Column(String(20), nullable=False, default="internal")
    deleted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False,
        default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        CheckConstraint(
            "event_type IN ('lesson', 'personal', 'other')",
            name="ck_calendar_event_type"
        ),
        CheckConstraint(
            "status IN ('scheduled', 'cancelled')",
            name="ck_calendar_event_status"
        ),
        CheckConstraint(
            "created_by IN ('internal', 'external')",
            name="ck_calendar_event_created_by"
        ),
        Index("ix_calendar_event_teacher_start",
              "teacher_user_id", "start_at"),
        Index("ix_calendar_event_student_start",
              "student_id", "start_at"),
    )


class CalendarEventSource(Base):
    __tablename__ = "calendar_event_sources"

    id = Column(Integer, primary_key=True, index=True)
    calendar_event_id = Column(
        Integer, ForeignKey("calendar_events.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    external_calendar_id = Column(
        Integer,
        ForeignKey("calendar_external_calendars.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    external_event_id = Column(String(500), nullable=False)
    external_etag = Column(String(500), nullable=True)
    external_updated_at = Column(DateTime, nullable=True)
    last_synced_at = Column(DateTime, nullable=True)
    sync_status = Column(String(30), nullable=False, default="pending")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint(
            "external_calendar_id", "external_event_id",
            name="uq_calendar_external_event"
        ),
        Index("ix_calendar_event_source_local",
              "calendar_event_id", "external_calendar_id"),
    )


class CalendarSyncLog(Base):
    __tablename__ = "calendar_sync_logs"

    id = Column(Integer, primary_key=True, index=True)
    connection_id = Column(
        Integer, ForeignKey("calendar_connections.id", ondelete="RESTRICT"),
        nullable=False, index=True
    )
    calendar_event_id = Column(
        Integer, ForeignKey("calendar_events.id", ondelete="SET NULL"),
        nullable=True, index=True
    )
    direction = Column(String(20), nullable=False)
    operation = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint(
            "direction IN ('inbound', 'outbound')",
            name="ck_calendar_sync_direction"
        ),
        CheckConstraint(
            "operation IN ('create', 'update', 'delete')",
            name="ck_calendar_sync_operation"
        ),
        CheckConstraint(
            "status IN ('success', 'failed')",
            name="ck_calendar_sync_status"
        ),
        Index("ix_calendar_sync_log_connection_created",
              "connection_id", "created_at"),
    )


class CalendarSyncConflict(Base):
    __tablename__ = "calendar_sync_conflicts"

    id = Column(Integer, primary_key=True, index=True)
    calendar_event_id = Column(
        Integer, ForeignKey("calendar_events.id", ondelete="SET NULL"),
        nullable=True, index=True
    )
    event_source_id = Column(
        Integer,
        ForeignKey("calendar_event_sources.id", ondelete="SET NULL"),
        nullable=True
    )
    conflict_type = Column(String(50), nullable=False)
    local_version = Column(Text, nullable=True)
    external_version = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="open")
    resolution = Column(Text, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint(
            "status IN ('open', 'resolved', 'ignored')",
            name="ck_calendar_conflict_status"
        ),
        Index("ix_calendar_conflict_status_created", "status", "created_at"),
    )
