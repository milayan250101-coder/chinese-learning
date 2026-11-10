from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.topic_models import Topic

router = APIRouter(prefix="/api/topics", tags=["话题库"])


class TopicCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    category: str | None = Field(default=None, max_length=100)
    description: str | None = None
    difficulty: str | None = Field(default=None, max_length=50)
    hsk_level: str | None = Field(default=None, max_length=50)


def topic_to_dict(topic: Topic):
    return {
        "id": topic.id,
        "name": topic.name,
        "category": topic.category,
        "description": topic.description,
        "difficulty": topic.difficulty,
        "hsk_level": topic.hsk_level,
        "source_type": topic.source_type,
        "status": topic.status,
        "created_at": topic.created_at,
        "updated_at": topic.updated_at,
    }


@router.get("")
def list_topics(
    status: str | None = Query(default=None),
    category: str | None = Query(default=None),
    hsk_level: str | None = Query(default=None),
    difficulty: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(Topic)

    if status:
        query = query.filter(Topic.status == status)
    if category:
        query = query.filter(Topic.category == category)
    if hsk_level:
        query = query.filter(Topic.hsk_level == hsk_level)
    if difficulty:
        query = query.filter(Topic.difficulty == difficulty)
    if keyword and keyword.strip():
        search = f"%{keyword.strip()}%"
        query = query.filter(
            Topic.name.ilike(search) |
            Topic.description.ilike(search)
        )

    topics = (
        query.order_by(Topic.name.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [topic_to_dict(topic) for topic in topics]


@router.post("", status_code=201)
def create_topic(
    data: TopicCreate,
    db: Session = Depends(get_db),
):
    name = data.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="话题名称不能为空")

    existing = db.query(Topic).filter(Topic.name == name).first()
    if existing:
        raise HTTPException(status_code=409, detail="该话题名称已存在")

    topic = Topic(
        name=name,
        category=data.category,
        description=data.description,
        difficulty=data.difficulty,
        hsk_level=data.hsk_level,
        source_type="manual",
        status="approved",
    )

    db.add(topic)
    db.commit()
    db.refresh(topic)

    return topic_to_dict(topic)


class TopicStatusUpdate(BaseModel):
    status: str


@router.patch("/{topic_id}/status")
def update_topic_status(
    topic_id: int,
    data: TopicStatusUpdate,
    db: Session = Depends(get_db),
):
    if data.status not in {"pending", "approved", "archived"}:
        raise HTTPException(status_code=422, detail="状态只能是 pending、approved 或 archived")

    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="话题不存在")

    topic.status = data.status
    db.commit()
    db.refresh(topic)
    return topic_to_dict(topic)


from backend.topic_models import TopicVocabulary, TopicExample


class ContentStatusUpdate(BaseModel):
    status: str


@router.patch("/vocabulary/{item_id}/status")
def update_vocabulary_status(item_id: int, data: ContentStatusUpdate, db: Session = Depends(get_db)):
    if data.status not in {"pending", "approved", "rejected"}:
        raise HTTPException(status_code=422, detail="状态只能是 pending、approved 或 rejected")
    item = db.query(TopicVocabulary).filter(TopicVocabulary.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="词汇记录不存在")
    item.status = data.status
    db.commit()
    db.refresh(item)
    return {"id": item.id, "chinese": item.chinese, "status": item.status}


@router.patch("/examples/{item_id}/status")
def update_example_status(item_id: int, data: ContentStatusUpdate, db: Session = Depends(get_db)):
    if data.status not in {"pending", "approved", "rejected"}:
        raise HTTPException(status_code=422, detail="状态只能是 pending、approved 或 rejected")
    item = db.query(TopicExample).filter(TopicExample.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="例句记录不存在")
    item.status = data.status
    db.commit()
    db.refresh(item)
    return {"id": item.id, "chinese": item.chinese, "status": item.status}
