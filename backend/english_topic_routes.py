import json
import os
from typing import Literal

import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

router = APIRouter()

DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = "deepseek-flash"


class EnglishTopicRequest(BaseModel):
    english_text: str = Field(min_length=20, max_length=20000)
    hsk_level: Literal["HSK1-3", "HSK4-5", "HSK6"]

    @field_validator("english_text")
    @classmethod
    def validate_english_text(cls, value):
        value = value.strip()
        if len(value) < 20:
            raise ValueError("英文内容至少需要20个字符。")
        return value


@router.post("/api/convert-english-topic")
def convert_english_topic(data: EnglishTopicRequest):
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="后端尚未配置 DeepSeek API 密钥。"
        )

    system_prompt = """
You are an expert international Chinese language teaching assistant.
Convert the supplied English trending topic or article into useful
Chinese learning materials for learners at the requested HSK level.

Return one valid JSON object only. Do not use Markdown fences.
The JSON must contain exactly these top-level fields:
{
  "topic_title_en": "English topic title",
  "topic_title_zh": "Chinese topic title",
  "topic_title_pinyin": "Pinyin of the Chinese title",
  "summary_zh": "A clear Chinese summary adapted to the requested HSK level",
  "vocabulary": [
    {"hanzi": "Chinese word", "pinyin": "Pinyin", "english": "English meaning"}
  ],
  "grammar_points": [
    {
      "point": "Chinese grammar point",
      "explanation_en": "Explanation in English",
      "example_zh": "Chinese example sentence",
      "example_en": "English translation"
    }
  ],
  "discussion_questions": [
    {"question_zh": "Question in Chinese", "question_en": "English translation"}
  ]
}

Requirements:
- Adapt the Chinese summary and examples to the requested HSK level.
- Provide accurate pinyin with tone marks.
- Include 8 to 12 useful vocabulary items.
- Include 3 to 5 practical grammar points.
- Include 3 to 5 discussion questions.
- Keep all English explanations and translations natural.
- Base the materials on the supplied source. Do not invent factual claims.
- Return valid JSON, with all required fields and arrays.
"""

    user_prompt = f"""
Requested learner level: {data.hsk_level}

English source material:
{data.english_text}

Please convert this material into the required Chinese teaching JSON.
"""

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
                    {"role": "user", "content": user_prompt}
                ],
                "thinking": {"type": "disabled"},
                "temperature": 0.2,
                "max_tokens": 4000,
                "response_format": {"type": "json_object"},
                "stream": False
            },
            timeout=120
        )
        response.raise_for_status()
        result = response.json()
        choice = result["choices"][0]

        if choice.get("finish_reason") == "length":
            raise ValueError("模型输出被截断，请缩短英文材料后重试。")

        raw = (choice["message"].get("content") or "").strip()
        if not raw:
            raise ValueError("模型返回了空内容，请重试。")

        parsed = json.loads(raw)

    except requests.RequestException:
        raise HTTPException(
            status_code=502,
            detail="调用 DeepSeek 服务失败，请稍后重试。"
        )
    except (KeyError, IndexError, TypeError, json.JSONDecodeError, ValueError):
        raise HTTPException(
            status_code=502,
            detail="模型返回的数据格式不正确或内容不完整，请重试。"
        )

    required_fields = [
        "topic_title_en",
        "topic_title_zh",
        "topic_title_pinyin",
        "summary_zh",
        "vocabulary",
        "grammar_points",
        "discussion_questions"
    ]

    if not isinstance(parsed, dict) or any(
        field not in parsed for field in required_fields
    ):
        raise HTTPException(
            status_code=502,
            detail="模型返回的数据缺少必要字段，请重试。"
        )

    list_fields = [
        "vocabulary",
        "grammar_points",
        "discussion_questions"
    ]
    if any(not isinstance(parsed[field], list) for field in list_fields):
        raise HTTPException(
            status_code=502,
            detail="模型返回的词汇、语法或讨论问题格式不正确。"
        )

    return parsed
