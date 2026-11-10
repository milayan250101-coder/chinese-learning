from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.hsk_models import HSKGrammarPoint


router = APIRouter(
    prefix="/api/hsk/grammar",
    tags=["HSK Grammar"],
)


@router.get("/")
def list_grammar_points(
    level: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    keyword: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(HSKGrammarPoint)

    if level:
        query = query.filter(HSKGrammarPoint.level == level)

    if category:
        query = query.filter(HSKGrammarPoint.category == category)

    if keyword:
        pattern = f"%{keyword}%"
        query = query.filter(
            HSKGrammarPoint.content.like(pattern)
            | HSKGrammarPoint.category.like(pattern)
            | HSKGrammarPoint.category_name.like(pattern)
            | HSKGrammarPoint.subcategory.like(pattern)
        )

    total = query.count()

    items = (
        query.order_by(
            HSKGrammarPoint.level,
            HSKGrammarPoint.source_index,
        )
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
                "id": item.id,
                "level": item.level,
                "category": item.category,
                "category_name": item.category_name,
                "subcategory": item.subcategory,
                "content": item.content,
                "syllabus_version": item.syllabus_version,
                "source_file": item.source_file,
            }
            for item in items
        ],
    }


@router.get("/levels")
def get_grammar_levels(db: Session = Depends(get_db)):
    rows = (
        db.query(
            HSKGrammarPoint.level,
        )
        .distinct()
        .order_by(HSKGrammarPoint.level)
        .all()
    )

    return {"levels": [row[0] for row in rows]}


@router.get("/{grammar_id}")
def get_grammar_point(
    grammar_id: int,
    db: Session = Depends(get_db),
):
    item = (
        db.query(HSKGrammarPoint)
        .filter(HSKGrammarPoint.id == grammar_id)
        .first()
    )

    if item is None:
        raise HTTPException(status_code=404, detail="Grammar point not found")

    return {
        "id": item.id,
        "level": item.level,
        "category": item.category,
        "category_name": item.category_name,
        "subcategory": item.subcategory,
        "content": item.content,
        "syllabus_version": item.syllabus_version,
        "source_file": item.source_file,
        "source_url": item.source_url,
    }
