"""Pydantic v2 schemas. Already complete — do not modify the field shapes,
but you may add validators if you need them.

These are the contract between extractor.py and main.py and between the
service and its callers. If you change a field, you change the contract.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


# ---------- shared sub-models ---------------------------------------------------

class Education(BaseModel):
    degree: Optional[str] = None
    branch: Optional[str] = None
    institute: Optional[str] = None
    year_end: Optional[int] = Field(None, ge=1950, le=2100)
    cgpa: Optional[float] = Field(None, ge=0, le=10)


class Experience(BaseModel):
    company: Optional[str] = None
    role: Optional[str] = None
    start: Optional[str] = None    # YYYY-MM
    end: Optional[str] = None      # YYYY-MM or "present"
    highlights: list[str] = Field(default_factory=list)


class Project(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    skills: list[str] = Field(default_factory=list)


class CompensationInr(BaseModel):
    min: Optional[float] = Field(None, ge=0)
    max: Optional[float] = Field(None, ge=0)


class ExperienceYears(BaseModel):
    min: Optional[float] = Field(None, ge=0)
    max: Optional[float] = Field(None, ge=0)


# ---------- response models -----------------------------------------------------

class Resume(BaseModel):
    candidate_name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    education: list[Education] = Field(default_factory=list)
    experience: list[Experience] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    raw_text_excerpt: str = ""
    model_used: str = ""
    parse_ms: int = 0

    @field_validator("skills", mode="before")
    @classmethod
    def lowercase_skills(cls, v):
        if not v:
            return []
        return [s.strip().lower() for s in v if isinstance(s, str) and s.strip()]


class JobDescription(BaseModel):
    company: Optional[str] = None
    role: str
    location: Optional[str] = None
    employment_type: Optional[Literal["full-time", "part-time", "internship", "contract"]] = None
    experience_required_years: ExperienceYears = Field(default_factory=ExperienceYears)
    must_have_skills: list[str] = Field(default_factory=list)
    good_to_have_skills: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    compensation_inr_lpa: CompensationInr = Field(default_factory=CompensationInr)
    raw_text_excerpt: str = ""
    model_used: str = ""
    parse_ms: int = 0

    @field_validator("must_have_skills", "good_to_have_skills", mode="before")
    @classmethod
    def lowercase_skills(cls, v):
        if not v:
            return []
        return [s.strip().lower() for s in v if isinstance(s, str) and s.strip()]


# ---------- DB row --------------------------------------------------------------

DocType = Literal["resume", "jd"]


class ParsedDocumentRow(BaseModel):
    id: Optional[int] = None
    content_hash: str
    doc_type: DocType
    raw_text: str
    parsed_json: dict
    model_used: str
    created_at: Optional[datetime] = None
