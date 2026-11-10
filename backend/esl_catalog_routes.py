from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.esl_catalog_models import ESLTopicCatalog

router = APIRouter(prefix="/api/esl-catalog", tags=["ESL Topic Catalog"])


@router.get("/topics")
def get_esl_catalog_topics(
    letter: Optional[str] = Query(default=None, min_length=1, max_length=1),
    category: Optional[str] = None,
    keyword: Optional[str] = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    query = db.query(ESLTopicCatalog)

    if letter:
        query = query.filter(ESLTopicCatalog.letter == letter.upper())

    if category:
        query = query.filter(ESLTopicCatalog.category == category)

    if keyword and keyword.strip():
        search = f"%{keyword.strip()}%"
        query = query.filter(
            (ESLTopicCatalog.title_en.ilike(search))
            | (ESLTopicCatalog.title_zh.ilike(search))
            | (ESLTopicCatalog.pinyin.ilike(search))
        )

    total = query.count()

    topics = (
        query.order_by(
            ESLTopicCatalog.category,
            ESLTopicCatalog.letter,
            ESLTopicCatalog.title_en
        )
        .offset(skip)
        .limit(limit)
        .all()
    )

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": [
            {
                "id": topic.id,
                "title_en": topic.title_en,
                "title_zh": topic.title_zh,
                "pinyin": topic.pinyin,
                "letter": topic.letter,
                "category": topic.category,
                "source_url": topic.source_url,
                "translation_status": topic.translation_status,
            }
            for topic in topics
        ],
    }
