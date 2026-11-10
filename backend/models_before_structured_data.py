from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from backend.database import Base

class LessonPlan(Base):
    __tablename__ = "lesson_plans"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), default="Untitled Lesson Plan")
    target_language = Column(String(50), default="English")
    hsk_level = Column(String(50), default="HSK1-3")
    original_text = Column(Text, nullable=True)
    generated_plan = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
