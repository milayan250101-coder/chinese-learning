import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend import auth_routes
from backend.auth_models import User
from backend.database import get_db
from backend.hsk_models import HSKVocabulary
from backend.grammar.models import GrammarKnowledgePoint

from backend.master_curriculum.models import (
    CoreVocabulary,
    CoreVocabularyHSKLink,
    CoreVocabularyGrammarLink,
    MasterCourseLevel,
    MasterCourseUnit,
    MasterUnitVocabulary,
    MasterUnitGrammarPoint,
    TeachingScenario,
    MasterUnitScenario,
)

from backend.master_curriculum import schemas

router = APIRouter(
    prefix="/api/master",
    tags=["教师Master词本位课程体系"],
)


def _owned_or_404(db, model, item_id, teacher_id):
    item = db.query(model).filter(
        model.id == item_id,
        model.teacher_user_id == teacher_id,
    ).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Resource not found.")
    return item


def _commit_or_conflict(db):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A conflicting or invalid relation already exists.",
        )


def _vocabulary_dict(item):
    return {
        "id": item.id,
        "simplified": item.simplified,
        "traditional": item.traditional,
        "pinyin": item.pinyin,
        "part_of_speech": item.part_of_speech,
        "definition": item.definition,
        "translations": json.loads(item.translations_json or "{}"),
        "teaching_notes": item.teaching_notes,
        "status": item.status,
    }


@router.get("/vocabularies")
def list_vocabularies(
    skip: int = 0,
    limit: int = 100,
    teacher: User = Depends(auth_routes.get_current_teacher),
    db: Session = Depends(get_db),
):
    if skip < 0 or limit < 1 or limit > 200:
        raise HTTPException(status_code=422, detail="Invalid pagination.")
    query = db.query(CoreVocabulary).filter(
        CoreVocabulary.teacher_user_id == teacher.id
    )
    total = query.count()
    items = query.order_by(
        CoreVocabulary.created_at.desc()
    ).offset(skip).limit(limit).all()
    return {
        "total": total,
        "items": [_vocabulary_dict(item) for item in items],
    }


@router.post("/vocabularies", status_code=201)
def create_vocabulary(
    payload: schemas.CoreVocabularyCreate,
    teacher: User = Depends(auth_routes.get_current_teacher),
    db: Session = Depends(get_db),
):
    item = CoreVocabulary(
        teacher_user_id=teacher.id,
        simplified=payload.simplified,
        traditional=payload.traditional,
        pinyin=payload.pinyin,
        part_of_speech=payload.part_of_speech,
        definition=payload.definition,
        translations_json=json.dumps(payload.translations, ensure_ascii=False),
        teaching_notes=payload.teaching_notes,
        status=payload.status,
    )
    db.add(item)
    _commit_or_conflict(db)
    db.refresh(item)
    return _vocabulary_dict(item)


def _level_dict(item):
    return {
        "id": item.id,
        "level_code": item.level_code,
        "title": item.title,
        "description": item.description,
        "sort_order": item.sort_order,
        "is_active": bool(item.is_active),
    }


@router.get("/levels")
def list_levels(
    teacher: User = Depends(auth_routes.get_current_teacher),
    db: Session = Depends(get_db),
):
    items = db.query(MasterCourseLevel).filter(
        MasterCourseLevel.teacher_user_id == teacher.id
    ).order_by(MasterCourseLevel.sort_order).all()
    return {"items": [_level_dict(item) for item in items]}


@router.post("/levels", status_code=201)
def create_level(
    payload: schemas.MasterCourseLevelCreate,
    teacher: User = Depends(auth_routes.get_current_teacher),
    db: Session = Depends(get_db),
):
    item = MasterCourseLevel(
        teacher_user_id=teacher.id,
        level_code=payload.level_code,
        title=payload.title,
        description=payload.description,
        sort_order=payload.sort_order,
        is_active=int(payload.is_active),
    )
    db.add(item)
    _commit_or_conflict(db)
    db.refresh(item)
    return _level_dict(item)


def _unit_dict(item):
    return {
        "id": item.id,
        "level_id": item.level_id,
        "parent_unit_id": item.parent_unit_id,
        "unit_code": item.unit_code,
        "title": item.title,
        "description": item.description,
        "teaching_objective": item.teaching_objective,
        "sort_order": item.sort_order,
        "status": item.status,
    }


@router.get("/units")
def list_units(
    level_id: int | None = None,
    teacher: User = Depends(auth_routes.get_current_teacher),
    db: Session = Depends(get_db),
):
    if level_id is not None:
        _owned_or_404(db, MasterCourseLevel, level_id, teacher.id)
    query = db.query(MasterCourseUnit).filter(
        MasterCourseUnit.teacher_user_id == teacher.id
    )
    if level_id is not None:
        query = query.filter(MasterCourseUnit.level_id == level_id)
    items = query.order_by(
        MasterCourseUnit.sort_order,
        MasterCourseUnit.id,
    ).all()
    return {"items": [_unit_dict(item) for item in items]}


@router.post("/units", status_code=201)
def create_unit(
    payload: schemas.MasterCourseUnitCreate,
    teacher: User = Depends(auth_routes.get_current_teacher),
    db: Session = Depends(get_db),
):
    _owned_or_404(db, MasterCourseLevel, payload.level_id, teacher.id)
    if payload.parent_unit_id is not None:
        parent = _owned_or_404(
            db, MasterCourseUnit, payload.parent_unit_id, teacher.id
        )
        if parent.level_id != payload.level_id:
            raise HTTPException(status_code=422, detail="Parent level mismatch.")
    item = MasterCourseUnit(
        teacher_user_id=teacher.id,
        level_id=payload.level_id,
        parent_unit_id=payload.parent_unit_id,
        unit_code=payload.unit_code,
        title=payload.title,
        description=payload.description,
        teaching_objective=payload.teaching_objective,
        sort_order=payload.sort_order,
        status=payload.status,
    )
    db.add(item)
    _commit_or_conflict(db)
    db.refresh(item)
    return _unit_dict(item)


def _scenario_dict(item):
    return {
        "id": item.id,
        "name": item.name,
        "domain": item.domain,
        "description": item.description,
        "target_tasks": item.target_tasks,
    }


@router.get("/scenarios")
def list_scenarios(
    teacher: User = Depends(auth_routes.get_current_teacher),
    db: Session = Depends(get_db),
):
    items = db.query(TeachingScenario).filter(
        TeachingScenario.teacher_user_id == teacher.id
    ).order_by(TeachingScenario.id.desc()).all()
    return {"items": [_scenario_dict(item) for item in items]}


@router.post("/scenarios", status_code=201)
def create_scenario(
    payload: schemas.TeachingScenarioCreate,
    teacher: User = Depends(auth_routes.get_current_teacher),
    db: Session = Depends(get_db),
):
    item = TeachingScenario(
        teacher_user_id=teacher.id,
        name=payload.name,
        domain=payload.domain,
        description=payload.description,
        target_tasks=payload.target_tasks,
    )
    db.add(item)
    _commit_or_conflict(db)
    db.refresh(item)
    return _scenario_dict(item)


@router.post("/vocabularies/{vocabulary_id}/hsk-links", status_code=201)
def link_vocabulary_to_hsk(
    vocabulary_id: int,
    payload: schemas.CoreVocabularyHSKLinkCreate,
    teacher: User = Depends(auth_routes.get_current_teacher),
    db: Session = Depends(get_db),
):
    _owned_or_404(db, CoreVocabulary, vocabulary_id, teacher.id)

    hsk_item = db.query(HSKVocabulary).filter(
        HSKVocabulary.id == payload.hsk_vocabulary_id
    ).first()
    if hsk_item is None:
        raise HTTPException(status_code=404, detail="HSK vocabulary not found.")

    item = CoreVocabularyHSKLink(
        core_vocabulary_id=vocabulary_id,
        hsk_vocabulary_id=hsk_item.id,
        mapping_type=payload.mapping_type,
    )
    db.add(item)
    _commit_or_conflict(db)
    db.refresh(item)
    return {
        "id": item.id,
        "core_vocabulary_id": item.core_vocabulary_id,
        "hsk_vocabulary_id": item.hsk_vocabulary_id,
        "mapping_type": item.mapping_type,
    }


@router.post("/vocabularies/{vocabulary_id}/grammar-links", status_code=201)
def link_vocabulary_to_grammar(
    vocabulary_id: int,
    payload: schemas.CoreVocabularyGrammarLinkCreate,
    teacher: User = Depends(auth_routes.get_current_teacher),
    db: Session = Depends(get_db),
):
    _owned_or_404(db, CoreVocabulary, vocabulary_id, teacher.id)
    _owned_or_404(db, GrammarKnowledgePoint, payload.grammar_point_id, teacher.id)

    item = CoreVocabularyGrammarLink(
        core_vocabulary_id=vocabulary_id,
        grammar_point_id=payload.grammar_point_id,
        relation_type=payload.relation_type,
        description=payload.description,
    )
    db.add(item)
    _commit_or_conflict(db)
    db.refresh(item)
    return {
        "id": item.id,
        "core_vocabulary_id": item.core_vocabulary_id,
        "grammar_point_id": item.grammar_point_id,
        "relation_type": item.relation_type,
        "description": item.description,
    }


@router.post("/units/{unit_id}/vocabulary-links", status_code=201)
def link_unit_to_vocabulary(
    unit_id: int,
    payload: schemas.MasterUnitVocabularyLinkCreate,
    teacher: User = Depends(auth_routes.get_current_teacher),
    db: Session = Depends(get_db),
):
    _owned_or_404(db, MasterCourseUnit, unit_id, teacher.id)
    _owned_or_404(db, CoreVocabulary, payload.core_vocabulary_id, teacher.id)

    item = MasterUnitVocabulary(
        unit_id=unit_id,
        core_vocabulary_id=payload.core_vocabulary_id,
        relation_type=payload.relation_type,
        sort_order=payload.sort_order,
    )
    db.add(item)
    _commit_or_conflict(db)
    db.refresh(item)
    return {
        "id": item.id,
        "unit_id": item.unit_id,
        "core_vocabulary_id": item.core_vocabulary_id,
        "relation_type": item.relation_type,
        "sort_order": item.sort_order,
    }


@router.post("/units/{unit_id}/grammar-links", status_code=201)
def link_unit_to_grammar(
    unit_id: int,
    payload: schemas.MasterUnitGrammarLinkCreate,
    teacher: User = Depends(auth_routes.get_current_teacher),
    db: Session = Depends(get_db),
):
    _owned_or_404(db, MasterCourseUnit, unit_id, teacher.id)
    _owned_or_404(db, GrammarKnowledgePoint, payload.grammar_point_id, teacher.id)

    item = MasterUnitGrammarPoint(
        unit_id=unit_id,
        grammar_point_id=payload.grammar_point_id,
        relation_type=payload.relation_type,
        sort_order=payload.sort_order,
    )
    db.add(item)
    _commit_or_conflict(db)
    db.refresh(item)
    return {
        "id": item.id,
        "unit_id": item.unit_id,
        "grammar_point_id": item.grammar_point_id,
        "relation_type": item.relation_type,
        "sort_order": item.sort_order,
    }


@router.post("/units/{unit_id}/scenario-links", status_code=201)
def link_unit_to_scenario(
    unit_id: int,
    payload: schemas.MasterUnitScenarioLinkCreate,
    teacher: User = Depends(auth_routes.get_current_teacher),
    db: Session = Depends(get_db),
):
    _owned_or_404(db, MasterCourseUnit, unit_id, teacher.id)
    _owned_or_404(db, TeachingScenario, payload.scenario_id, teacher.id)

    item = MasterUnitScenario(
        unit_id=unit_id,
        scenario_id=payload.scenario_id,
        sort_order=payload.sort_order,
    )
    db.add(item)
    _commit_or_conflict(db)
    db.refresh(item)
    return {
        "id": item.id,
        "unit_id": item.unit_id,
        "scenario_id": item.scenario_id,
        "sort_order": item.sort_order,
    }
