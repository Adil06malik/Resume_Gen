from pydantic import BaseModel, EmailStr, HttpUrl, Field
from typing import Optional, List
from datetime import datetime


class CandidateInfo(BaseModel):
    name: str = ""
    email: EmailStr | str = ""
    phone: str = ""
    location: str = ""
    links: List[str] = []


class Skill(BaseModel):
    name: str
    category: Optional[str] = None
    proficiency: Optional[str] = None


class Experience(BaseModel):
    title: str
    company: str
    location: str = ""
    start_date: str
    end_date: str = ""
    description: List[str] = []
    technologies: List[str] = []


class Project(BaseModel):
    name: str
    description: str
    technologies: List[str] = []
    url: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class Education(BaseModel):
    degree: str
    institution: str
    location: str = ""
    graduation_date: str = ""
    gpa: Optional[str] = None


class Certification(BaseModel):
    name: str
    issuer: str
    date: str = ""
    url: Optional[str] = None


class StructuredResume(BaseModel):
    candidate: CandidateInfo = CandidateInfo()
    summary: str = ""
    skills: List[Skill] = []
    experience: List[Experience] = []
    projects: List[Project] = []
    education: List[Education] = []
    certifications: List[Certification] = []


class ResumeCreate(BaseModel):
    pass


class ResumeResponse(BaseModel):
    id: int
    filename: str
    file_path: str
    raw_text: Optional[str] = None
    structured_data: Optional[StructuredResume] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ResumeUploadResponse(BaseModel):
    id: int
    filename: str
    message: str