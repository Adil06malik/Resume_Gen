import os
import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.models.resume import Resume
from app.models.job import Job
from app.models.application import Application
from app.models.resume_version import ResumeVersion
from app.models.cover_letter import CoverLetter
from app.schemas.application import (
    ApplicationCreate,
    ApplicationResponse,
    ApplicationDetail,
    ApplicationHistoryItem,
    StatusUpdate,
    ResumeMatchResult,
    ATSScore,
)
from app.schemas.resume import StructuredResume
from app.schemas.job import JobRequirements
from app.routers.auth import get_current_user
from app.services.resume_matcher import ResumeMatcherService
from app.services.resume_tailor import ResumeTailorService
from app.services.ats_analyzer import ATSAnalyzerService
from app.services.cover_letter import CoverLetterService
from app.services.pdf_generator import PDFGeneratorService
from app.services.docx_generator import DOCXGeneratorService

router = APIRouter()


@router.post("/", response_model=ApplicationResponse, status_code=201)
async def create_application(
    req: ApplicationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Resume).where(Resume.id == req.resume_id, Resume.user_id == current_user.id)
    )
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    result = await db.execute(
        select(Job).where(Job.id == req.job_id, Job.user_id == current_user.id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    application = Application(
        user_id=current_user.id,
        resume_id=req.resume_id,
        job_id=req.job_id,
    )
    db.add(application)
    await db.commit()
    await db.refresh(application)
    return application


@router.get("/", response_model=list[ApplicationResponse])
async def list_applications(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Application).where(Application.user_id == current_user.id).order_by(Application.created_at.desc())
    )
    return result.scalars().all()


@router.get("/history", response_model=list[ApplicationHistoryItem])
async def application_history(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Application, Job, ResumeVersion)
        .join(Job, Application.job_id == Job.id)
        .outerjoin(ResumeVersion, ResumeVersion.application_id == Application.id)
        .where(Application.user_id == current_user.id)
        .order_by(Application.created_at.desc())
    )
    rows = result.all()
    items = []
    seen = set()
    for app, job, rv in rows:
        if app.id in seen:
            continue
        seen.add(app.id)
        items.append(ApplicationHistoryItem(
            id=app.id,
            company=job.company,
            job_title=job.title,
            ats_score=app.ats_score,
            resume_version=rv.version if rv else 1,
            status=app.status,
            created_at=app.created_at,
        ))
    return items


@router.get("/{app_id}", response_model=ApplicationDetail)
async def get_application(
    app_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Application).where(Application.id == app_id, Application.user_id == current_user.id)
    )
    application = result.scalar_one_or_none()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    match_result = None
    ats_analysis = None
    tailored_resume = None
    cover_letter_text = None

    rv_result = await db.execute(
        select(ResumeVersion).where(ResumeVersion.application_id == app_id).order_by(ResumeVersion.version.desc())
    )
    latest_version = rv_result.scalar_one_or_none()
    if latest_version:
        try:
            tailored_resume = StructuredResume.model_validate_json(latest_version.content)
        except Exception:
            pass

    cl_result = await db.execute(
        select(CoverLetter).where(CoverLetter.application_id == app_id).order_by(CoverLetter.created_at.desc())
    )
    latest_cl = cl_result.scalar_one_or_none()
    if latest_cl:
        cover_letter_text = latest_cl.content

    return ApplicationDetail(
        id=application.id,
        resume_id=application.resume_id,
        job_id=application.job_id,
        status=application.status,
        ats_score=application.ats_score,
        match_result=match_result,
        ats_analysis=ats_analysis,
        tailored_resume=tailored_resume,
        cover_letter=cover_letter_text,
        created_at=application.created_at,
        updated_at=application.updated_at,
    )


@router.put("/{app_id}/status", response_model=ApplicationResponse)
async def update_status(
    app_id: int,
    req: StatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Application).where(Application.id == app_id, Application.user_id == current_user.id)
    )
    application = result.scalar_one_or_none()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    application.status = req.status
    await db.commit()
    await db.refresh(application)
    return application


@router.post("/{app_id}/match", response_model=ResumeMatchResult)
async def match_resume(
    app_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Application).where(Application.id == app_id, Application.user_id == current_user.id)
    )
    application = result.scalar_one_or_none()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    resume = await db.get(Resume, application.resume_id)
    job = await db.get(Job, application.job_id)

    if not resume or not resume.structured_data:
        raise HTTPException(status_code=400, detail="Resume has no parsed data")
    if not job or not job.structured_requirements:
        raise HTTPException(status_code=400, detail="Job has no structured requirements")

    structured_resume = StructuredResume.model_validate_json(resume.structured_data)
    job_requirements = JobRequirements.model_validate_json(job.structured_requirements)

    matcher = ResumeMatcherService()
    try:
        match_result = await matcher.match_resume(structured_resume, job_requirements)
    finally:
        await matcher.close()

    return match_result


@router.post("/{app_id}/tailor", response_model=ApplicationDetail)
async def tailor_resume(
    app_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Application).where(Application.id == app_id, Application.user_id == current_user.id)
    )
    application = result.scalar_one_or_none()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    resume = await db.get(Resume, application.resume_id)
    job = await db.get(Job, application.job_id)

    if not resume or not resume.structured_data:
        raise HTTPException(status_code=400, detail="Resume has no parsed data")
    if not job or not job.structured_requirements:
        raise HTTPException(status_code=400, detail="Job has no structured requirements")

    structured_resume = StructuredResume.model_validate_json(resume.structured_data)
    job_requirements = JobRequirements.model_validate_json(job.structured_requirements)

    matcher = ResumeMatcherService()
    try:
        match_result = await matcher.match_resume(structured_resume, job_requirements)
    finally:
        await matcher.close()

    tailor = ResumeTailorService()
    try:
        tailored = await tailor.tailor_resume(
            structured_resume, job_requirements, match_result, job.title, job.company
        )
    finally:
        await tailor.close()

    existing_rv = await db.execute(
        select(ResumeVersion).where(ResumeVersion.application_id == app_id).order_by(ResumeVersion.version.desc())
    )
    latest = existing_rv.scalar_one_or_none()
    new_version = (latest.version + 1) if latest else 1

    rv = ResumeVersion(
        application_id=app_id,
        version=new_version,
        content=tailored.model_dump_json(),
    )
    db.add(rv)
    await db.commit()
    await db.refresh(rv)

    try:
        pdf_gen = PDFGeneratorService()
        docx_gen = DOCXGeneratorService()
        rv.pdf_path = pdf_gen.generate_resume_pdf(tailored, job.company, job.title)
        rv.docx_path = docx_gen.generate_resume_docx(tailored, job.company, job.title)
        await db.commit()
    except Exception:
        pass

    return ApplicationDetail(
        id=application.id,
        resume_id=application.resume_id,
        job_id=application.job_id,
        status=application.status,
        ats_score=application.ats_score,
        match_result=match_result,
        ats_analysis=None,
        tailored_resume=tailored,
        cover_letter=None,
        created_at=application.created_at,
        updated_at=application.updated_at,
    )


@router.post("/{app_id}/ats", response_model=ATSScore)
async def analyze_ats(
    app_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Application).where(Application.id == app_id, Application.user_id == current_user.id)
    )
    application = result.scalar_one_or_none()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    resume = await db.get(Resume, application.resume_id)
    job = await db.get(Job, application.job_id)

    if not resume or not resume.structured_data:
        raise HTTPException(status_code=400, detail="Resume has no parsed data")
    if not job or not job.structured_requirements:
        raise HTTPException(status_code=400, detail="Job has no structured requirements")

    structured_resume = StructuredResume.model_validate_json(resume.structured_data)
    job_requirements = JobRequirements.model_validate_json(job.structured_requirements)

    rv_result = await db.execute(
        select(ResumeVersion).where(ResumeVersion.application_id == app_id).order_by(ResumeVersion.version.desc())
    )
    latest_rv = rv_result.scalar_one_or_none()
    if latest_rv:
        try:
            structured_resume = StructuredResume.model_validate_json(latest_rv.content)
        except Exception:
            pass

    matcher = ResumeMatcherService()
    try:
        match_result = await matcher.match_resume(structured_resume, job_requirements)
    finally:
        await matcher.close()

    ats_analyzer = ATSAnalyzerService()
    try:
        ats_score = await ats_analyzer.analyze_ats(structured_resume, job_requirements, match_result)
    finally:
        await ats_analyzer.close()

    application.ats_score = ats_score.overall_score
    await db.commit()

    return ats_score


@router.post("/{app_id}/cover-letter")
async def generate_cover_letter(
    app_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Application).where(Application.id == app_id, Application.user_id == current_user.id)
    )
    application = result.scalar_one_or_none()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    resume = await db.get(Resume, application.resume_id)
    job = await db.get(Job, application.job_id)

    if not resume or not resume.structured_data:
        raise HTTPException(status_code=400, detail="Resume has no parsed data")
    if not job or not job.structured_requirements:
        raise HTTPException(status_code=400, detail="Job has no structured requirements")

    structured_resume = StructuredResume.model_validate_json(resume.structured_data)
    job_requirements = JobRequirements.model_validate_json(job.structured_requirements)

    matcher = ResumeMatcherService()
    try:
        match_result = await matcher.match_resume(structured_resume, job_requirements)
    finally:
        await matcher.close()

    cl_service = CoverLetterService()
    try:
        cover_letter_text = await cl_service.generate_cover_letter(
            structured_resume, job_requirements, match_result, job.title, job.company
        )
    finally:
        await cl_service.close()

    cl = CoverLetter(application_id=app_id, content=cover_letter_text)
    db.add(cl)
    await db.commit()
    await db.refresh(cl)

    try:
        pdf_gen = PDFGeneratorService()
        cl.pdf_path = pdf_gen.generate_cover_letter_pdf(cover_letter_text, job.company, job.title)
        await db.commit()
    except Exception:
        pass

    return {"cover_letter": cover_letter_text}


@router.delete("/{app_id}")
async def delete_application(
    app_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Application).where(Application.id == app_id, Application.user_id == current_user.id)
    )
    application = result.scalar_one_or_none()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    await db.delete(application)
    await db.commit()
    return {"message": "Application deleted"}
