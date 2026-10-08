import os
import json
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.models.resume import Resume
from app.schemas.resume import ResumeResponse, ResumeUploadResponse, StructuredResume
from app.routers.auth import get_current_user
from app.services.resume_parser import ResumeParserService

router = APIRouter()


@router.post("/upload", response_model=ResumeUploadResponse)
async def upload_resume(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    allowed = {".pdf", ".docx", ".txt"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed:
        raise HTTPException(status_code=400, detail=f"Unsupported file format: {ext}")

    file_size = 0
    contents = await file.read()
    file_size = len(contents)
    if file_size > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail="File too large")

    save_path = os.path.join(settings.UPLOAD_DIR, f"{current_user.id}_{file.filename}")
    with open(save_path, "wb") as f:
        f.write(contents)

    resume = Resume(
        user_id=current_user.id,
        filename=file.filename,
        file_path=save_path,
    )
    db.add(resume)
    await db.commit()
    await db.refresh(resume)

    parser = ResumeParserService()
    try:
        raw_text = await parser.extract_text(save_path)
        resume.raw_text = raw_text
        structured = await parser.parse_resume(raw_text)
        resume.structured_data = structured.model_dump_json()
        await db.commit()
        await db.refresh(resume)
    except Exception:
        pass
    finally:
        await parser.close()

    return ResumeUploadResponse(id=resume.id, filename=resume.filename, message="Resume uploaded and parsed")


@router.get("/", response_model=list[ResumeResponse])
async def list_resumes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Resume).where(Resume.user_id == current_user.id).order_by(Resume.created_at.desc())
    )
    resumes = result.scalars().all()
    responses = []
    for r in resumes:
        sd = None
        if r.structured_data:
            try:
                sd = StructuredResume.model_validate_json(r.structured_data)
            except Exception:
                pass
        responses.append(ResumeResponse(
            id=r.id,
            filename=r.filename,
            file_path=r.file_path,
            raw_text=r.raw_text,
            structured_data=sd,
            created_at=r.created_at,
            updated_at=r.updated_at,
        ))
    return responses


@router.get("/{resume_id}", response_model=ResumeResponse)
async def get_resume(
    resume_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Resume).where(Resume.id == resume_id, Resume.user_id == current_user.id)
    )
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    sd = None
    if resume.structured_data:
        try:
            sd = StructuredResume.model_validate_json(resume.structured_data)
        except Exception:
            pass
    return ResumeResponse(
        id=resume.id,
        filename=resume.filename,
        file_path=resume.file_path,
        raw_text=resume.raw_text,
        structured_data=sd,
        created_at=resume.created_at,
        updated_at=resume.updated_at,
    )


@router.delete("/{resume_id}")
async def delete_resume(
    resume_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Resume).where(Resume.id == resume_id, Resume.user_id == current_user.id)
    )
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    if os.path.exists(resume.file_path):
        os.remove(resume.file_path)

    await db.delete(resume)
    await db.commit()
    return {"message": "Resume deleted"}
