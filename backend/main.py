import re
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends
from sqlalchemy.orm import Session
from pypdf import PdfReader
from docx import Document
from io import BytesIO
import os
import json
import requests

from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

from backend.database import engine, Base, get_db
from backend import auth_routes
from backend import student_routes
from backend.student_knowledge import routes as student_knowledge_routes
from backend.models import LessonPlan
from backend import topic_routes
from backend import topic_models
from backend import esl_catalog_models
from backend import auth_models
from backend import english_topic_routes
from backend import esl_catalog_routes
from backend import hsk_models
from backend import hsk_hanzi_models
from backend import student_profile_models
from backend import hsk_routes
from backend import hsk_vocabulary_routes

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Chinese Learning Teaching Hub API")
app.include_router(auth_routes.router)
app.include_router(student_routes.router)
app.include_router(student_knowledge_routes.router)
app.include_router(topic_routes.router)
app.include_router(english_topic_routes.router)
app.include_router(esl_catalog_routes.router)
app.include_router(hsk_routes.router)
app.include_router(hsk_vocabulary_routes.router)

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
    db: Session = Depends(get_db),
    teacher: auth_models.User = Depends(auth_routes.get_current_teacher),
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

        structured_data_json = None
        try:
            structured_data = generate_structured_data(
                text_content=text_content,
                filename=filename,
                target_lang=target_lang,
                hsk_level=hsk_level,
                generated_plan=generated_plan
            )
            structured_data_json = json.dumps(
                structured_data,
                ensure_ascii=False
            )
        except (requests.RequestException, RuntimeError, ValueError) as exc:
            print(f"Structured data generation failed: {exc}")

        new_record = LessonPlan(
            title=filename,
            target_language=target_lang,
            hsk_level=hsk_level,
            original_text=text_content[:50000],
            generated_plan=generated_plan,
            structured_data=structured_data_json,
            teacher_user_id=teacher.id,
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
        import traceback
        traceback.print_exc()
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="An unexpected server error occurred."
        )


@app.get("/api/history")
def get_history(
    db: Session = Depends(get_db),
    teacher: auth_models.User = Depends(auth_routes.get_current_teacher),
):
    records = (
        db.query(LessonPlan)
        .filter(LessonPlan.teacher_user_id == teacher.id)
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
    db: Session = Depends(get_db),
    teacher: auth_models.User = Depends(auth_routes.get_current_teacher),
):
    record = (
        db.query(LessonPlan)
        .filter(
            LessonPlan.id == record_id,
            LessonPlan.teacher_user_id == teacher.id,
        )
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
        "generated_plan": record.generated_plan,
        "original_text": record.original_text,
        "structured_data": (
            json.loads(record.structured_data)
            if record.structured_data
            else None
        )
    }

def generate_structured_data(
    text_content: str,
    filename: str,
    target_lang: str,
    hsk_level: str,
    generated_plan: str
) -> dict:
    """Generate structured teaching data in three smaller DeepSeek requests."""

    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is not available.")

    common_rules = f"""
You are an expert Chinese language teaching assistant.
All explanations and translations must use {target_lang}.
Keep Chinese text in Chinese and provide accurate pinyin wherever applicable.
Use only information supported by the original notes and lesson plan.
Never invent vocabulary, examples, pronunciation, answers, or HSK levels.
Use an empty string when a detail cannot be reliably provided.
Every item must have a meaningful Chinese headword or title.
Never use generic labels such as Item 1 or 项目一.
Return one valid JSON object only, without Markdown fences.
"""

    source_material = f"""
Filename: {filename}
Target language: {target_lang}
HSK level: {hsk_level}

Original notes:
{text_content}

Generated lesson plan:
{generated_plan}
"""

    batches = [
        {
            "keys": ["vocabulary", "grammar", "sentence_patterns"],
            "schema": """
Return exactly these three arrays:
{
  "vocabulary": [
    {"chinese":"汉字词汇","pinyin":"准确拼音","translation":"目标语言翻译","part_of_speech":"词性","note":"补充说明"}
  ],
  "grammar": [
    {"point":"语法名称","pinyin":"适用时填写拼音","explanation":"中文解释","translation":"目标语言解释","example":"中文例句","example_pinyin":"例句拼音","example_translation":"例句翻译"}
  ],
  "sentence_patterns": [
    {"pattern":"中文句型","pinyin":"拼音","translation":"目标语言翻译","example":"中文例句","example_pinyin":"例句拼音","example_translation":"例句翻译"}
  ]
}
""",
            "tokens": 3000
        },
        {
            "keys": ["examples", "pronunciation", "exercises"],
            "schema": """
Return exactly these three arrays:
{
  "examples": [
    {"chinese":"中文例句","pinyin":"准确拼音","translation":"目标语言翻译","note":"教学说明"}
  ],
  "pronunciation": [
    {"chinese":"具体汉字或词汇","pinyin":"准确拼音","pronunciation_note":"发音说明","translation":"目标语言释义"}
  ],
  "exercises": [
    {"type":"练习类型","title":"具体练习标题","instruction":"练习要求","question":"具体题目","answer":"有依据时填写参考答案"}
  ]
}
""",
            "tokens": 3000
        },
        {
            "keys": ["hsk_mapping"],
            "schema": """
Return exactly this array:
{
  "hsk_mapping": [
    {"chinese":"具体词汇或语法项目","pinyin":"拼音","level":"有依据的HSK等级，否则留空","translation":"目标语言翻译","reason":"定级依据；无法判断时说明"}
  ]
}
HSK recommendations must be conservative and evidence-based. Never guess a level.
""",
            "tokens": 1800
        }
    ]

    combined = {
        "vocabulary": [],
        "grammar": [],
        "sentence_patterns": [],
        "examples": [],
        "pronunciation": [],
        "exercises": [],
        "hsk_mapping": []
    }

    for batch in batches:
        batch_data = None
        last_error = None

        system_prompt = common_rules + "\n" + batch["schema"]

        user_prompt = (
            source_material
            + "\nGenerate only the requested arrays. "
            + "Keep every item concise but useful for teaching."
        )

        for attempt in range(2):
            retry_note = ""
            if attempt == 1:
                retry_note = (
                    "\nYour previous attempt failed. Regenerate a complete, "
                    "valid JSON object. Keep the output concise and do not omit "
                    "any requested array."
                )

            try:
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
                            {
                                "role": "user",
                                "content": user_prompt + retry_note
                            }
                        ],
                        "thinking": {"type": "disabled"},
                        "temperature": 0.2,
                        "max_tokens": batch["tokens"],
                        "response_format": {"type": "json_object"},
                        "stream": False
                    },
                    timeout=120
                )

                if not response.ok:
                    raise RuntimeError(
                        f"DeepSeek request failed: HTTP {response.status_code}"
                    )

                result = response.json()
                choice = result["choices"][0]
                raw = (choice["message"]["content"] or "").strip()

                if choice.get("finish_reason") == "length":
                    raise ValueError("DeepSeek output was truncated.")

                if raw.startswith("```"):
                    raw = raw.split("\n", 1)[-1]
                    raw = raw.rsplit("```", 1)[0].strip()

                start_json = raw.find("{")
                end_json = raw.rfind("}")

                if start_json < 0 or end_json < start_json:
                    raise ValueError("No complete JSON object was returned.")

                batch_data = json.loads(raw[start_json:end_json + 1])

                if not isinstance(batch_data, dict):
                    raise ValueError("Response must be a JSON object.")

                for key in batch["keys"]:
                    if key not in batch_data:
                        raise ValueError(f"Missing JSON array: {key}")
                    if not isinstance(batch_data[key], list):
                        raise ValueError(f"Invalid JSON array: {key}")

                break

            except Exception as exc:
                last_error = exc
                batch_data = None

        if batch_data is None:
            raise RuntimeError(
                f"Structured data batch {batch['keys']} failed after "
                f"2 attempts: {last_error}"
            )

        for key in batch["keys"]:
            combined[key] = batch_data[key]

    return combined


# ==================== HSK 3.0 词汇接口 ====================
import requests
from fastapi import HTTPException

HSK3_BASE_URL = "https://raw.githubusercontent.com/koynoyno/hsk3.0-json/main"
hsk_cache = {}

@app.get("/api/hsk3/{level}")
def get_hsk3_words(level: int):
    if level < 1 or level > 9:
        raise HTTPException(status_code=400, detail="HSK 级别必须在 1 到 9 之间")
    if level in hsk_cache:
        return {"status": "success", "level": level, "total": len(hsk_cache[level]), "words": hsk_cache[level]}
    url = f"{HSK3_BASE_URL}/hsk{level}.json"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            words_data = res.json()
            hsk_cache[level] = words_data
            return {"status": "success", "level": level, "total": len(words_data), "words": words_data}
        else:
            raise HTTPException(status_code=404, detail=f"未找到 HSK {level} 级的 JSON 文件")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"无法从 GitHub 获取 HSK 数据: {str(e)}")
