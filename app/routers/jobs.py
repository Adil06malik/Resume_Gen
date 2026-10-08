from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.models.job import Job
from app.schemas.job import JobCreate, JobResponse, JobRequirements
from app.routers.auth import get_current_user
from app.services.job_analyzer import JobAnalyzerService

router = APIRouter()


@router.post("/", response_model=JobResponse, status_code=201)
async def create_job(
    req: JobCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = Job(
        user_id=current_user.id,
        title=req.title,
        company=req.company,
        url=str(req.url) if req.url else None,
        description=req.description,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    analyzer = JobAnalyzerService()
    try:
        requirements = await analyzer.analyze_job(req.title, req.company, req.description)
        job.structured_requirements = requirements.model_dump_json()
        await db.commit()
        await db.refresh(job)
    except Exception:
        pass
    finally:
        await analyzer.close()

    sr = None
    if job.structured_requirements:
        try:
            sr = JobRequirements.model_validate_json(job.structured_requirements)
        except Exception:
            pass
    return JobResponse(
        id=job.id,
        title=job.title,
        company=job.company,
        url=job.url,
        description=job.description,
        structured_requirements=sr,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


@router.get("/", response_model=list[JobResponse])
async def list_jobs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Job).where(Job.user_id == current_user.id).order_by(Job.created_at.desc())
    )
    jobs = result.scalars().all()
    responses = []
    for j in jobs:
        sr = None
        if j.structured_requirements:
            try:
                sr = JobRequirements.model_validate_json(j.structured_requirements)
            except Exception:
                pass
        responses.append(JobResponse(
            id=j.id,
            title=j.title,
            company=j.company,
            url=j.url,
            description=j.description,
            structured_requirements=sr,
            created_at=j.created_at,
            updated_at=j.updated_at,
        ))
    return responses


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Job).where(Job.id == job_id, Job.user_id == current_user.id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    sr = None
    if job.structured_requirements:
        try:
            sr = JobRequirements.model_validate_json(job.structured_requirements)
        except Exception:
            pass
    return JobResponse(
        id=job.id,
        title=job.title,
        company=job.company,
        url=job.url,
        description=job.description,
        structured_requirements=sr,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


@router.delete("/{job_id}")
async def delete_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Job).where(Job.id == job_id, Job.user_id == current_user.id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    await db.delete(job)
    await db.commit()
    return {"message": "Job deleted"}
