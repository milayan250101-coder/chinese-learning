from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends
from sqlalchemy.orm import Session
import os

from backend.database import engine, Base, get_db
from backend.models import LessonPlan

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Chinese Learning Teaching Hub API")

@app.get("/")
def read_root():
    return {"message": "Chinese Learning Teaching Hub Backend (Global) is Running!"}

@app.post("/api/process-document")
async def process_document(
    file: UploadFile = File(...),
    target_lang: str = Form("English"),
    hsk_level: str = Form("HSK1-3"),
    db: Session = Depends(get_db)
):
    try:
        content = await file.read()
        text_content = content.decode("utf-8", errors="ignore")
        
        generated_plan = f"""# 📚 智能中文教案

## 1. 课程概述
- **目标语言**: {target_lang}
- **HSK 级别**: {hsk_level}
- **文件名**: {file.filename}

## 2. 核心词汇与句型
- 欢迎 (huānyíng) - Welcome
- 学习 (xuéxí) - Study / Learn

## 3. 课文摘要
{text_content[:300]}...
"""

        new_record = LessonPlan(
            title=file.filename or "Untitled Lesson",
            target_language=target_lang,
            hsk_level=hsk_level,
            original_text=text_content[:500],
            generated_plan=generated_plan
        )
        db.add(new_record)
        db.commit()
        db.refresh(new_record)

        return {
            "status": "success",
            "record_id": new_record.id,
            "content": generated_plan
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/history")
def get_history(db: Session = Depends(get_db)):
    records = db.query(LessonPlan).order_by(LessonPlan.created_at.desc()).all()
    return [
        {
            "id": r.id,
            "title": r.title,
            "target_language": r.target_language,
            "hsk_level": r.hsk_level,
            "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S")
        }
        for r in records
    ]

@app.get("/api/history/{record_id}")
def get_history_detail(record_id: int, db: Session = Depends(get_db)):
    record = db.query(LessonPlan).filter(LessonPlan.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    return {
        "id": record.id,
        "title": record.title,
        "target_language": record.target_language,
        "hsk_level": record.hsk_level,
        "created_at": record.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "generated_plan": record.generated_plan
    }
