from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    parent_id: Optional[int] = None
    description: Optional[str] = None
    sort_order: int = 0

    @field_validator("name")
    @classmethod
    def clean_name(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("分类名称不能为空")
        return value


class LevelMappingCreate(BaseModel):
    level_code: str
    mapping_type: Literal["introduced", "review", "extension"] = "introduced"

    @field_validator("level_code")
    @classmethod
    def validate_level(cls, value):
        value = value.strip()
        allowed = {f"HSK {number}" for number in range(1, 10)}
        if value not in allowed:
            raise ValueError("等级必须使用 HSK 1 至 HSK 9 格式")
        return value


class GrammarPointCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    normalized_name: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = None
    teaching_objective: Optional[str] = None

    source_item_no: Optional[int] = Field(default=None, ge=1)
    original_name: Optional[str] = None

    primary_category_id: Optional[int] = None
    category_ids: list[int] = Field(default_factory=list)
    levels: list[LevelMappingCreate] = Field(default_factory=list)

    status: Literal["draft", "published", "archived"] = "draft"
    sort_order: int = 0

    @field_validator("title")
    @classmethod
    def clean_title(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("知识点名称不能为空")
        return value

    @field_validator("normalized_name")
    @classmethod
    def clean_normalized_name(cls, value):
        return value.strip() if value else value
