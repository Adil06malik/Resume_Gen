from pydantic import BaseModel
from typing import List, Optional


class ATSScoreResponse(BaseModel):
    overall_score: float
    keyword_score: float
    skills_score: float
    experience_score: float
    responsibility_score: float
    formatting_score: float
    matched_keywords: List[str]
    missing_keywords: List[str]
    matched_requirements: List[str]
    partial_requirements: List[str]
    missing_requirements: List[str]


class ATSAnalysisRequest(BaseModel):
    resume_content: str
    job_requirements: dict