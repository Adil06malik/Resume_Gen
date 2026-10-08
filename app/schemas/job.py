from pydantic import BaseModel, HttpUrl
from typing import Optional, List
from datetime import datetime


class JobRequirements(BaseModel):
    required_skills: List[str] = []
    preferred_skills: List[str] = []
    responsibilities: List[str] = []
    experience_requirements: List[str] = []
    education_requirements: List[str] = []
    certifications: List[str] = []
    keywords: List[str] = []
    soft_skills: List[str] = []
    domain: str = ""


class JobCreate(BaseModel):
    title: str
    company: str
    url: Optional[HttpUrl] = None
    description: str


class JobResponse(BaseModel):
    id: int
    title: str
    company: str
    url: Optional[str] = None
    description: str
    structured_requirements: Optional[JobRequirements] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True