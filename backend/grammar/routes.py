from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from backend import auth_routes
from backend.auth_models import User
from backend.database import get_db
from backend.grammar.models import (
    GrammarCategory,
    GrammarKnowledgePoint,
    GrammarPointCategory,
    GrammarPointLevel,
    GrammarRule,
    GrammarExample,
    GrammarPitfall,
)
from backend.grammar.schemas import CategoryCreate, GrammarPointCreate

router = APIRouter(
    prefix="/api/grammar",
    tags=["教师语法知识库"],
)


def visible_categories(db: Session, teacher_id: int):
    return db.query(GrammarCategory).filter(
        or_(
            GrammarCategory.owner_teacher_id == teacher_id,
            GrammarCategory.owner_teacher_id.is_(None),
        ),
        GrammarCategory.is_active == 1,
    )


def category_dict(item):
    return {
        "id": item.id,
        "parent_id": item.parent_id,
        "name": item.name,
        "description": item.description,
        "sort_order": item.sort_order,
        "is_shared": item.owner_teacher_id is None,
    }


def point_dict(item, db: Session):
    categories = (
        db.query(GrammarCategory)
        .join(
            GrammarPointCategory,
            GrammarPointCategory.category_id == GrammarCategory.id,
        )
        .filter(GrammarPointCategory.grammar_point_id == item.id)
        .order_by(GrammarPointCategory.is_primary.desc(), GrammarCategory.sort_order)
        .all()
    )

    # 兼容只有主分类、尚未建立关联记录的知识点
    if not categories and item.primary_category_id:
        category = db.query(GrammarCategory).filter(
            GrammarCategory.id == item.primary_category_id
        ).first()
        if category:
            categories = [category]

    levels = (
        db.query(GrammarPointLevel)
        .filter(GrammarPointLevel.grammar_point_id == item.id)
        .order_by(GrammarPointLevel.level_code)
        .all()
    )

    return {
        "id": item.id,
        "title": item.title,
        "normalized_name": item.normalized_name,
        "description": item.description,
        "teaching_objective": item.teaching_objective,
        "source_item_no": item.source_item_no,
        "original_name": item.original_name,
        "primary_category_id": item.primary_category_id,
        "categories": [category_dict(c) for c in categories],
        "levels": [
            {
                "level_code": level.level_code,
                "mapping_type": level.mapping_type,
            }
            for level in levels
        ],
        "status": item.status,
        "sort_order": item.sort_order,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


@router.get("/categories")
def list_categories(
    db: Session = Depends(get_db),
    teacher: User = Depends(auth_routes.get_current_teacher),
):
    items = (
        visible_categories(db, teacher.id)
        .order_by(GrammarCategory.sort_order, GrammarCategory.id)
        .all()
    )
    return [category_dict(item) for item in items]


@router.post("/categories", status_code=201)
def create_category(
    payload: CategoryCreate,
    db: Session = Depends(get_db),
    teacher: User = Depends(auth_routes.get_current_teacher),
):
    if payload.parent_id is not None:
        parent = visible_categories(db, teacher.id).filter(
            GrammarCategory.id == payload.parent_id
        ).first()
        if parent is None:
            raise HTTPException(status_code=404, detail="父分类不存在或无权使用")

    duplicate = visible_categories(db, teacher.id).filter(
        func.lower(GrammarCategory.name) == payload.name.lower(),
        GrammarCategory.parent_id == payload.parent_id,
    ).first()
    if duplicate:
        raise HTTPException(status_code=409, detail="同一层级已存在同名分类")

    item = GrammarCategory(
        owner_teacher_id=teacher.id,
        parent_id=payload.parent_id,
        name=payload.name,
        description=payload.description,
        sort_order=payload.sort_order,
        is_active=1,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return category_dict(item)


@router.get("/points")
def list_grammar_points(
    category_id: Optional[int] = Query(default=None, ge=1),
    level: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    keyword: Optional[str] = Query(default=None, min_length=1, max_length=100),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    teacher: User = Depends(auth_routes.get_current_teacher),
):
    query = db.query(GrammarKnowledgePoint).filter(
        GrammarKnowledgePoint.teacher_user_id == teacher.id
    )

    if category_id is not None:
        allowed_category = visible_categories(db, teacher.id).filter(
            GrammarCategory.id == category_id
        ).first()
        if allowed_category is None:
            raise HTTPException(status_code=404, detail="分类不存在或无权使用")

        query = query.outerjoin(
            GrammarPointCategory,
            GrammarPointCategory.grammar_point_id == GrammarKnowledgePoint.id,
        ).filter(
            or_(
                GrammarPointCategory.category_id == category_id,
                GrammarKnowledgePoint.primary_category_id == category_id,
            )
        )

    if level:
        if level not in {f"HSK {n}" for n in range(1, 10)}:
            raise HTTPException(status_code=422, detail="等级格式应为 HSK 1 至 HSK 9")
        query = query.join(
            GrammarPointLevel,
            GrammarPointLevel.grammar_point_id == GrammarKnowledgePoint.id,
        ).filter(GrammarPointLevel.level_code == level)

    if status:
        if status not in {"draft", "published", "archived"}:
            raise HTTPException(status_code=422, detail="无效的知识点状态")
        query = query.filter(GrammarKnowledgePoint.status == status)

    if keyword and keyword.strip():
        term = f"%{keyword.strip()}%"
        query = query.filter(
            or_(
                GrammarKnowledgePoint.title.ilike(term),
                GrammarKnowledgePoint.normalized_name.ilike(term),
                GrammarKnowledgePoint.original_name.ilike(term),
                GrammarKnowledgePoint.description.ilike(term),
            )
        )

    total = query.distinct().count()
    items = (
        query.distinct()
        .order_by(
            GrammarKnowledgePoint.sort_order,
            GrammarKnowledgePoint.id,
        )
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [point_dict(item, db) for item in items],
    }


@router.post("/points", status_code=201)
def create_grammar_point(
    payload: GrammarPointCreate,
    db: Session = Depends(get_db),
    teacher: User = Depends(auth_routes.get_current_teacher),
):
    category_ids = list(dict.fromkeys(payload.category_ids))
    if payload.primary_category_id is not None:
        if payload.primary_category_id not in category_ids:
            category_ids.insert(0, payload.primary_category_id)

    if category_ids:
        categories = visible_categories(db, teacher.id).filter(
            GrammarCategory.id.in_(category_ids)
        ).all()
        if len(categories) != len(category_ids):
            raise HTTPException(status_code=422, detail="分类列表包含不存在或无权使用的分类")

    if payload.primary_category_id is not None and payload.primary_category_id not in category_ids:
        raise HTTPException(status_code=422, detail="主分类必须属于分类列表")

    level_codes = [level.level_code for level in payload.levels]
    if len(level_codes) != len(set(level_codes)):
        raise HTTPException(status_code=422, detail="同一知识点不能重复关联同一个 HSK 等级")

    item = GrammarKnowledgePoint(
        teacher_user_id=teacher.id,
        primary_category_id=payload.primary_category_id,
        source_item_no=payload.source_item_no,
        original_name=payload.original_name,
        title=payload.title,
        normalized_name=payload.normalized_name,
        description=payload.description,
        teaching_objective=payload.teaching_objective,
        status=payload.status,
        sort_order=payload.sort_order,
    )

    try:
        db.add(item)
        db.flush()

        for category_id in category_ids:
            db.add(
                GrammarPointCategory(
                    grammar_point_id=item.id,
                    category_id=category_id,
                    is_primary=1 if category_id == payload.primary_category_id else 0,
                )
            )

        for level in payload.levels:
            db.add(
                GrammarPointLevel(
                    grammar_point_id=item.id,
                    level_code=level.level_code,
                    mapping_type=level.mapping_type,
                )
            )

        db.commit()
        db.refresh(item)
    except Exception:
        db.rollback()
        raise

    return point_dict(item, db)


@router.get("/points/{point_id}")
def get_grammar_point(
    point_id: int,
    db: Session = Depends(get_db),
    teacher: User = Depends(auth_routes.get_current_teacher),
):
    item = db.query(GrammarKnowledgePoint).filter(
        GrammarKnowledgePoint.id == point_id,
        GrammarKnowledgePoint.teacher_user_id == teacher.id,
    ).first()

    if item is None:
        raise HTTPException(status_code=404, detail="知识点不存在")

    result = point_dict(item, db)
    result["rules"] = [
        {
            "id": rule.id,
            "rule_type": rule.rule_type,
            "formula": rule.formula,
            "explanation": rule.explanation,
            "sort_order": rule.sort_order,
        }
        for rule in db.query(GrammarRule)
        .filter(GrammarRule.grammar_point_id == item.id)
        .order_by(GrammarRule.sort_order, GrammarRule.id)
        .all()
    ]
    result["examples"] = [
        {
            "id": example.id,
            "chinese_text": example.chinese_text,
            "pinyin": example.pinyin,
            "translations_json": example.translations_json,
            "explanation": example.explanation,
            "sort_order": example.sort_order,
        }
        for example in db.query(GrammarExample)
        .filter(GrammarExample.grammar_point_id == item.id)
        .order_by(GrammarExample.sort_order, GrammarExample.id)
        .all()
    ]
    result["pitfalls"] = [
        {
            "id": pitfall.id,
            "title": pitfall.title,
            "incorrect_example": pitfall.incorrect_example,
            "correct_example": pitfall.correct_example,
            "explanation": pitfall.explanation,
            "sort_order": pitfall.sort_order,
        }
        for pitfall in db.query(GrammarPitfall)
        .filter(GrammarPitfall.grammar_point_id == item.id)
        .order_by(GrammarPitfall.sort_order, GrammarPitfall.id)
        .all()
    ]
    return result
