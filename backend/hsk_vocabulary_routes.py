from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.hsk_models import HSKVocabulary

router = APIRouter(
    prefix="/api/hsk/vocabulary",
    tags=["HSK Vocabulary"],
)

LEVEL_ORDER = [
    "HSK 1",
    "HSK 2",
    "HSK 3",
    "HSK 4",
    "HSK 5",
    "HSK 6",
    "HSK 7–9",
]


@router.get("/levels")
def get_vocabulary_levels(db: Session = Depends(get_db)):
    existing = {
        row[0]
        for row in db.query(HSKVocabulary.level).distinct().all()
    }
    return [level for level in LEVEL_ORDER if level in existing]


@router.get("/")
def list_vocabulary(
    level: Optional[str] = Query(default=None),
    keyword: Optional[str] = Query(default=None, min_length=1, max_length=100),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(HSKVocabulary)

    if level:
        query = query.filter(HSKVocabulary.level == level)

    if keyword and keyword.strip():
        term = f"%{keyword.strip()}%"
        query = query.filter(
            HSKVocabulary.simplified.ilike(term)
            | HSKVocabulary.traditional.ilike(term)
            | HSKVocabulary.pinyin.ilike(term)
            | HSKVocabulary.english.ilike(term)
            | HSKVocabulary.part_of_speech.ilike(term)
        )

    total = query.count()
    items = (
        query.order_by(HSKVocabulary.number)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "number": item.number,
                "level": item.level,
                "simplified": item.simplified,
                "traditional": item.traditional,
                "pinyin": item.pinyin,
                "english": item.english,
                "part_of_speech": item.part_of_speech,
            }
            for item in items
        ],
    }

@router.get("/{number}")
def get_vocabulary_detail(number: int, db: Session = Depends(get_db)):
    item = (
        db.query(HSKVocabulary)
        .filter(HSKVocabulary.number == number)
        .first()
    )

    if item is None:
        raise HTTPException(
            status_code=404,
            detail="Vocabulary item not found"
        )

    return {
        "number": item.number,
        "level": item.level,
        "simplified": item.simplified,
        "traditional": item.traditional,
        "pinyin": item.pinyin,
        "english": item.english,
        "part_of_speech": item.part_of_speech,
    }
