import os
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse

from app.config import settings
from app.models.user import User
from app.routers.auth import get_current_user
from app.services.pipeline import TailorPipeline, slugify
from app.services.resume_diff import compute_diff
from app.services import progress as progress_tracker

router = APIRouter()

ALLOWED_EXTS = {".pdf", ".docx", ".txt"}


async def _download(out_dir: str, filename: str, media_type: str):
    path = Path(out_dir) / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"{filename} not found")
    return FileResponse(
        path=str(path),
        media_type=media_type,
        filename=filename,
        content_disposition_type="attachment",
    )


@router.post("/tailor")
async def tailor(
    resume_file: UploadFile = File(...),
    job_title: str = Form(""),
    company: str = Form(""),
    job_description: str = Form(...),
    progress_token: str = Form(""),
    current_user: User = Depends(get_current_user),
):
    ext = os.path.splitext(resume_file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTS:
        raise HTTPException(status_code=400, detail=f"Unsupported file format: {ext}")

    contents = await resume_file.read()
    if len(contents) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail="File too large")

    if not job_description.strip():
        raise HTTPException(status_code=400, detail="Job description is required")

    run_id = f"{int(time.time())}_{uuid.uuid4().hex[:6]}"
    out_dir = str(Path(settings.UPLOAD_DIR) / "tailored" / str(current_user.id) / run_id)
    os.makedirs(out_dir, exist_ok=True)

    token = progress_token or f"p_{uuid.uuid4().hex[:12]}"
    progress_tracker.create(token)

    tmp_input = str(Path(out_dir) / f"source{ext}")
    with open(tmp_input, "wb") as f:
        f.write(contents)

    pipeline = TailorPipeline()
    try:
        result = await pipeline.run(
            resume_file_path=tmp_input,
            job_title=job_title,
            company=company,
            job_description=job_description,
            out_dir=out_dir,
            progress_token=token,
        )
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to tailor resume: {e}")

    result["run_id"] = run_id
    result["download_base"] = f"/api/tailor/{current_user.id}/{run_id}"
    if result.get("original_resume") and result.get("tailored_resume"):
        result["diff"] = compute_diff(result["original_resume"], result["tailored_resume"])
    return JSONResponse(content=result)


@router.get("/tailor/progress/{token}")
async def tailor_progress(token: str, current_user: User = Depends(get_current_user)):
    info = progress_tracker.get(token)
    if not info:
        return JSONResponse(content={"step": "done", "message": "", "percent": 100, "error": None})
    return JSONResponse(
        content={
            "step": info.get("step", "started"),
            "message": info.get("message", ""),
            "percent": progress_tracker.percent_for(token),
            "error": info.get("error"),
        }
    )


@router.get("/tailor/{user_id}/{run_id}/resume/pdf")
async def download_resume_pdf(user_id: int, run_id: str, current_user: User = Depends(get_current_user)):
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    out_dir = str(Path(settings.UPLOAD_DIR) / "tailored" / str(user_id) / run_id)
    return await _download(out_dir, "tailored_resume.pdf", "application/pdf")


@router.get("/tailor/{user_id}/{run_id}/resume/docx")
async def download_resume_docx(user_id: int, run_id: str, current_user: User = Depends(get_current_user)):
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    out_dir = str(Path(settings.UPLOAD_DIR) / "tailored" / str(user_id) / run_id)
    return await _download(
        out_dir,
        "tailored_resume.docx",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@router.get("/tailor/{user_id}/{run_id}/resume/txt")
async def download_resume_txt(user_id: int, run_id: str, current_user: User = Depends(get_current_user)):
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    out_dir = str(Path(settings.UPLOAD_DIR) / "tailored" / str(user_id) / run_id)
    return await _download(out_dir, "tailored_resume.txt", "text/plain")


@router.get("/tailor/{user_id}/{run_id}/cover-letter/pdf")
async def download_cover_letter_pdf(user_id: int, run_id: str, current_user: User = Depends(get_current_user)):
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    out_dir = str(Path(settings.UPLOAD_DIR) / "tailored" / str(user_id) / run_id)
    return await _download(out_dir, "cover_letter.pdf", "application/pdf")


@router.get("/tailor/{user_id}/{run_id}/cover-letter/txt")
async def download_cover_letter_txt(user_id: int, run_id: str, current_user: User = Depends(get_current_user)):
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    out_dir = str(Path(settings.UPLOAD_DIR) / "tailored" / str(user_id) / run_id)
    return await _download(out_dir, "cover_letter.txt", "text/plain")
