from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends
from sqlalchemy.orm import Session
from pypdf import PdfReader
from docx import Document
from io import BytesIO
import os
import json
import requests

from backend.database import engine, Base, get_db
from backend.models import LessonPlan

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Chinese Learning Teaching Hub API")

DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = "deepseek-flash"


@app.get("/")
def read_root():
    return {
        "message": "Chinese Learning Teaching Hub Backend is Running!"
    }


def extract_document_text(filename: str, content: bytes) -> str:
    extension = os.path.splitext(filename.lower())[1]

    try:
        if extension == ".txt":
            return content.decode("utf-8-sig")

        elif extension == ".pdf":
            reader = PdfReader(BytesIO(content))
            return "\n".join(
                page.extract_text() or "" for page in reader.pages
            )

        elif extension == ".docx":
            document = Document(BytesIO(content))
            paragraphs = [
                paragraph.text
                for paragraph in document.paragraphs
                if paragraph.text.strip()
            ]
            return "\n".join(paragraphs)

        else:
            raise ValueError(
                "Unsupported file type. Please upload TXT, PDF, or DOCX."
            )

    except Exception as exc:
        raise ValueError(f"Could not read document: {exc}") from exc


def generate_lesson_plan(
    text_content: str,
    filename: str,
    target_lang: str,
    hsk_level: str
) -> str:
    api_key = os.environ.get("DEEPSEEK_API_KEY")

    if not api_key:
        raise RuntimeError(
            "DEEPSEEK_API_KEY is not available in the backend environment."
        )

    system_prompt = """
You are an experienced Chinese language teaching assistant.

Create a practical, well-organized Chinese lesson plan based only
on the teacher's uploaded notes.

Requirements:
1. Preserve the teacher's original teaching intentions.
2. Identify key Chinese vocabulary and sentence patterns.
3. Include accurate pinyin for Chinese words and sentences.
4. Explain the content in the requested target language.
5. Adapt explanations and activities to the requested HSK level.
6. Include grammar explanations and example sentences.
7. Suggest classroom exercises and review activities.
8. Do not invent content that contradicts the uploaded notes.
9. If information is missing, clearly say so instead of guessing.

Use clear Markdown headings and structured sections.
"""

    user_prompt = f"""
Please create a Chinese lesson plan using the following information.

File name: {filename}
Target explanation language: {target_lang}
HSK level: {hsk_level}

Teacher's uploaded notes:

{text_content}
"""

    response = requests.post(
        DEEPSEEK_API_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json={
            "model": DEEPSEEK_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "thinking": {"type": "disabled"},
            "temperature": 0.7,
            "max_tokens": 6000,
            "stream": False
        },
        timeout=120
    )

    if not response.ok:
        raise RuntimeError(
            f"DeepSeek API request failed (HTTP {response.status_code}). "
            "Please check the API configuration and account balance."
        )

    result = response.json()
    generated_text = (
        result.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
    )

    if not generated_text.strip():
        raise RuntimeError("DeepSeek returned an empty lesson plan.")

    return generated_text


@app.post("/api/process-document")
async def process_document(
    file: UploadFile = File(...),
    target_lang: str = Form("English"),
    hsk_level: str = Form("HSK1-3"),
    db: Session = Depends(get_db)
):
    try:
        content = await file.read()

        if not content:
            raise HTTPException(
                status_code=400,
                detail="The uploaded file is empty."
            )

        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(
                status_code=413,
                detail="File is too large. Maximum size is 10 MB."
            )

        filename = file.filename or "Untitled Lesson"

        text_content = extract_document_text(filename, content)

        if not text_content.strip():
            raise HTTPException(
                status_code=400,
                detail="No readable text was found in the uploaded file."
            )

        if len(text_content) > 50000:
            text_content = text_content[:50000]

        generated_plan = generate_lesson_plan(
            text_content=text_content,
            filename=filename,
            target_lang=target_lang,
            hsk_level=hsk_level
        )

        new_record = LessonPlan(
            title=filename,
            target_language=target_lang,
            hsk_level=hsk_level,
            original_text=text_content[:50000],
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

    except HTTPException:
        raise

    except requests.Timeout:
        db.rollback()
        raise HTTPException(
            status_code=504,
            detail="DeepSeek request timed out. Please try again."
        )

    except requests.RequestException:
        db.rollback()
        raise HTTPException(
            status_code=502,
            detail="Could not connect to DeepSeek. Please try again."
        )

    except RuntimeError as exc:
        db.rollback()
        raise HTTPException(status_code=502, detail=str(exc))

    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="An unexpected server error occurred."
        )


@app.get("/api/history")
def get_history(db: Session = Depends(get_db)):
    records = (
        db.query(LessonPlan)
        .order_by(LessonPlan.created_at.desc())
        .all()
    )

    return [
        {
            "id": record.id,
            "title": record.title,
            "target_language": record.target_language,
            "hsk_level": record.hsk_level,
            "created_at": record.created_at.strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        }
        for record in records
    ]


@app.get("/api/history/{record_id}")
def get_history_detail(
    record_id: int,
    db: Session = Depends(get_db)
):
    record = (
        db.query(LessonPlan)
        .filter(LessonPlan.id == record_id)
        .first()
    )

    if not record:
        raise HTTPException(
            status_code=404,
            detail="Record not found"
        )

    return {
        "id": record.id,
        "title": record.title,
        "target_language": record.target_language,
        "hsk_level": record.hsk_level,
        "created_at": record.created_at.strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
        "generated_plan": record.generated_plan
    }

def generate_structured_data(
    text_content: str,
    filename: str,
    target_lang: str,
    hsk_level: str,
    generated_plan: str
) -> dict:
    """Generate structured Chinese teaching data using DeepSeek."""

    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is not available.")

    system_prompt = """
You are an expert Chinese language teaching assistant.

Return a valid JSON object only, without Markdown code fences.

Required structure:
{
  "vocabulary": [],
  "grammar": [],
  "sentence_patterns": [],
  "examples": [],
  "pronunciation": [],
  "exercises": [],
  "hsk_mapping": []
}

Use the original notes and lesson plan.
Do not invent unsupported information.
Use English explanations and accurate Chinese pinyin.
Use empty arrays when information is unavailable.
"""

    user_prompt = f"""
Filename: {filename}
Target language: {target_lang}
HSK level: {hsk_level}

Original notes:
{text_content}

Generated lesson plan:
{generated_plan}
"""

    response = requests.post(
        DEEPSEEK_API_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json={
            "model": DEEPSEEK_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "thinking": {"type": "disabled"},
            "temperature": 0.2,
            "max_tokens": 6000,
            "stream": False
        },
        timeout=120
    )

    if not response.ok:
        raise RuntimeError(
            f"DeepSeek JSON request failed: HTTP {response.status_code}"
        )

    raw = response.json()["choices"][0]["message"]["content"].strip()

    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        raw = raw.rsplit("```", 1)[0].strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("DeepSeek returned invalid JSON.") from exc

    if not isinstance(data, dict):
        raise RuntimeError("Structured data must be a JSON object.")

    required_keys = [
        "vocabulary",
        "grammar",
        "sentence_patterns",
        "examples",
        "pronunciation",
        "exercises",
        "hsk_mapping"
    ]

    for key in required_keys:
        if key not in data:
            data[key] = []
        if not isinstance(data[key], list):
            raise RuntimeError(f"Invalid JSON field: {key}")

    return data
