import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.models.application import Application
from app.models.resume_version import ResumeVersion
from app.models.cover_letter import CoverLetter
from app.schemas.resume import StructuredResume
from app.routers.auth import get_current_user
from app.services.pdf_generator import PDFGeneratorService
from app.services.docx_generator import DOCXGeneratorService

router = APIRouter()


async def _get_authorized_app(
    app_id: int,
    db: AsyncSession,
    current_user: User,
) -> Application:
    result = await db.execute(
        select(Application).where(Application.id == app_id, Application.user_id == current_user.id)
    )
    application = result.scalar_one_or_none()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    return application


@router.post("/applications/{app_id}/generate-documents")
async def generate_documents(
    app_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    application = await _get_authorized_app(app_id, db, current_user)

    from app.models.job import Job
    job = await db.get(Job, application.job_id)
    if not job or not job.structured_requirements:
        raise HTTPException(status_code=400, detail="Job has no structured requirements")

    rv_result = await db.execute(
        select(ResumeVersion).where(ResumeVersion.application_id == app_id).order_by(ResumeVersion.version.desc())
    )
    latest_rv = rv_result.scalar_one_or_none()
    if not latest_rv:
        raise HTTPException(status_code=400, detail="No tailored resume found. Run tailor first.")

    try:
        tailored_resume = StructuredResume.model_validate_json(latest_rv.content)
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to parse tailored resume data")

    pdf_gen = PDFGeneratorService()
    docx_gen = DOCXGeneratorService()

    pdf_path = pdf_gen.generate_resume_pdf(tailored_resume, job.company, job.title)
    docx_path = docx_gen.generate_resume_docx(tailored_resume, job.company, job.title)

    latest_rv.pdf_path = pdf_path
    latest_rv.docx_path = docx_path
    await db.commit()

    cl_result = await db.execute(
        select(CoverLetter).where(CoverLetter.application_id == app_id).order_by(CoverLetter.created_at.desc())
    )
    latest_cl = cl_result.scalar_one_or_none()
    if latest_cl and not latest_cl.pdf_path:
        cl_pdf_path = pdf_gen.generate_cover_letter_pdf(latest_cl.content, job.company, job.title)
        latest_cl.pdf_path = cl_pdf_path
        await db.commit()

    return {
        "resume_pdf": pdf_path,
        "resume_docx": docx_path,
        "cover_letter_pdf": latest_cl.pdf_path if latest_cl else None,
    }


@router.get("/applications/{app_id}/resume/pdf")
async def download_resume_pdf(
    app_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    application = await _get_authorized_app(app_id, db, current_user)

    rv_result = await db.execute(
        select(ResumeVersion).where(ResumeVersion.application_id == app_id).order_by(ResumeVersion.version.desc())
    )
    latest_rv = rv_result.scalar_one_or_none()
    if not latest_rv or not latest_rv.pdf_path:
        raise HTTPException(status_code=404, detail="Resume PDF not found. Generate documents first.")
    if not os.path.exists(latest_rv.pdf_path):
        raise HTTPException(status_code=404, detail="Resume PDF file missing from disk.")

    from app.models.job import Job
    job = await db.get(Job, application.job_id)
    filename = os.path.basename(latest_rv.pdf_path)

    return FileResponse(
        path=latest_rv.pdf_path,
        media_type="application/pdf",
        filename=filename,
    )


@router.get("/applications/{app_id}/resume/docx")
async def download_resume_docx(
    app_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    application = await _get_authorized_app(app_id, db, current_user)

    rv_result = await db.execute(
        select(ResumeVersion).where(ResumeVersion.application_id == app_id).order_by(ResumeVersion.version.desc())
    )
    latest_rv = rv_result.scalar_one_or_none()
    if not latest_rv or not latest_rv.docx_path:
        raise HTTPException(status_code=404, detail="Resume DOCX not found. Generate documents first.")
    if not os.path.exists(latest_rv.docx_path):
        raise HTTPException(status_code=404, detail="Resume DOCX file missing from disk.")

    filename = os.path.basename(latest_rv.docx_path)

    return FileResponse(
        path=latest_rv.docx_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=filename,
    )


@router.get("/applications/{app_id}/cover-letter/pdf")
async def download_cover_letter_pdf(
    app_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    application = await _get_authorized_app(app_id, db, current_user)

    cl_result = await db.execute(
        select(CoverLetter).where(CoverLetter.application_id == app_id).order_by(CoverLetter.created_at.desc())
    )
    latest_cl = cl_result.scalar_one_or_none()
    if not latest_cl or not latest_cl.pdf_path:
        raise HTTPException(status_code=404, detail="Cover letter PDF not found. Generate documents first.")
    if not os.path.exists(latest_cl.pdf_path):
        raise HTTPException(status_code=404, detail="Cover letter PDF file missing from disk.")

    filename = os.path.basename(latest_cl.pdf_path)

    return FileResponse(
        path=latest_cl.pdf_path,
        media_type="application/pdf",
        filename=filename,
    )
