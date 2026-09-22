"""Pydantic models for projects."""

from typing import Optional

from pydantic import BaseModel, Field, field_validator


def sanitize_name(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("Name cannot be empty")
    if len(cleaned) > 200:
        raise ValueError("Name must be 200 characters or fewer")
    cleaned = "".join(ch for ch in cleaned if ch.isprintable())
    return cleaned


class ProjectBase(BaseModel):
    name: str
    description: str = ""
    enabled: bool = True

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        return sanitize_name(v)

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        return (v or "").strip()[:1000]


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return sanitize_name(v)

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return v.strip()[:1000]


class Project(ProjectBase):
    id: str
    created_at: str
    updated_at: str
