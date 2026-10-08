from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.schemas.resume import StructuredResume
from app.schemas.job import JobRequirements


class RequirementMatch(BaseModel):
    requirement: str
    status: str
    evidence: str = ""


class ResumeMatchResult(BaseModel):
    matched_requirements: List[RequirementMatch] = []
    partial_requirements: List[RequirementMatch] = []
    missing_requirements: List[RequirementMatch] = []


class ATSScore(BaseModel):
    overall_score: float = 0.0
    keyword_score: float = 0.0
    skills_score: float = 0.0
    experience_score: float = 0.0
    responsibility_score: float = 0.0
    formatting_score: float = 0.0
    matched_keywords: List[str] = []
    missing_keywords: List[str] = []
    matched_requirements: List[str] = []
    partial_requirements: List[str] = []
    missing_requirements: List[str] = []


class ApplicationCreate(BaseModel):
    resume_id: int
    job_id: int


class ApplicationResponse(BaseModel):
    id: int
    resume_id: int
    job_id: int
    status: str
    ats_score: Optional[float] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ApplicationDetail(BaseModel):
    id: int
    resume_id: int
    job_id: int
    status: str
    ats_score: Optional[float] = None
    match_result: Optional[ResumeMatchResult] = None
    ats_analysis: Optional[ATSScore] = None
    tailored_resume: Optional[StructuredResume] = None
    cover_letter: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ApplicationHistoryItem(BaseModel):
    id: int
    company: str
    job_title: str
    ats_score: Optional[float] = None
    resume_version: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class StatusUpdate(BaseModel):
    status: str