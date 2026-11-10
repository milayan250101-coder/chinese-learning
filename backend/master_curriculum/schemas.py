from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator


class CoreVocabularyCreate(BaseModel):
    simplified: str = Field(min_length=1, max_length=100)
    traditional: Optional[str] = Field(default=None, max_length=100)
    pinyin: str = Field(min_length=1, max_length=200)
    part_of_speech: str = Field(default="未标注", max_length=100)
    definition: Optional[str] = None
    translations: dict[str, str] = Field(default_factory=dict)
    teaching_notes: Optional[str] = None
    status: Literal["draft", "published", "archived"] = "draft"

    @field_validator("simplified", "pinyin", "part_of_speech")
    @classmethod
    def clean_required_text(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("该字段不能为空")
        return value


class MasterCourseLevelCreate(BaseModel):
    level_code: Literal["MASTER-1", "MASTER-2", "MASTER-3"]
    title: str = Field(min_length=1, max_length=150)
    description: Optional[str] = None
    sort_order: int = 0
    is_active: bool = True

    @field_validator("title")
    @classmethod
    def clean_title(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("课程等级名称不能为空")
        return value


class MasterCourseUnitCreate(BaseModel):
    level_id: int = Field(gt=0)
    parent_unit_id: Optional[int] = Field(default=None, gt=0)
    unit_code: str = Field(min_length=1, max_length=50)
    title: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    teaching_objective: Optional[str] = None
    sort_order: int = 0
    status: Literal["draft", "published", "archived"] = "draft"

    @field_validator("unit_code", "title")
    @classmethod
    def clean_text(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("单元编号和名称不能为空")
        return value


class TeachingScenarioCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    domain: str = Field(default="日常生活", max_length=100)
    description: Optional[str] = None
    target_tasks: Optional[str] = None

    @field_validator("name", "domain")
    @classmethod
    def clean_text(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("场景名称和领域不能为空")
        return value


class CoreVocabularyHSKLinkCreate(BaseModel):
    hsk_vocabulary_id: int = Field(gt=0)
    mapping_type: Literal["introduced", "review", "extension"] = "introduced"


class CoreVocabularyGrammarLinkCreate(BaseModel):
    grammar_point_id: int = Field(gt=0)
    relation_type: str = Field(default="uses", max_length=50)
    description: Optional[str] = None


class MasterUnitVocabularyLinkCreate(BaseModel):
    core_vocabulary_id: int = Field(gt=0)
    relation_type: Literal["core", "support", "extension"] = "core"
    sort_order: int = 0


class MasterUnitGrammarLinkCreate(BaseModel):
    grammar_point_id: int = Field(gt=0)
    relation_type: str = Field(default="core", max_length=50)
    sort_order: int = 0


class MasterUnitScenarioLinkCreate(BaseModel):
    scenario_id: int = Field(gt=0)
    sort_order: int = 0
