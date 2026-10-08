"""Command-line resume tailor.

Usage:
    python tailor.py [options]

Flow (resume -> tailored resume + cover letter for a job description):
    1. Load the master resume from the resume path (default: a PDF/DOCX/TXT in uploads/)
    2. Load the job description from input/job.txt
    3. Parse resume -> structured, analyze job -> requirements
    4. Match resume to job, tailor the resume around the job
    5. Generate a custom cover letter
    6. Score the result for ATS
    7. Write tailored resume + cover letter to output/ as PDF, DOCX, and TXT

The master resume is NEVER modified.
"""

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path

from app.config import settings
from app.schemas.application import ResumeMatchResult
from app.schemas.job import JobRequirements
from app.schemas.resume import StructuredResume
from app.services.ats_analyzer import ATSAnalyzerService
from app.services.cover_letter import CoverLetterService
from app.services.docx_generator import DOCXGeneratorService
from app.services.job_analyzer import JobAnalyzerService
from app.services.pdf_generator import PDFGeneratorService
from app.services.resume_matcher import ResumeMatcherService
from app.services.resume_parser import ResumeParserService
from app.services.resume_tailor import ResumeTailorService

BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "output"


def pick_resume_path(arg: str | None) -> Path:
    if arg:
        path = Path(arg)
        if path.exists():
            return path
        raise FileNotFoundError(f"Resume not found: {arg}")

    uploads = BASE_DIR / "uploads"
    candidates = list(uploads.glob("*.pdf")) + list(uploads.glob("*.docx")) + list(uploads.glob("*.txt"))
    if not candidates:
        raise FileNotFoundError(
            f"No resume (pdf/docx/txt) found in {uploads}. "
            "Place your master resume there or pass --resume <path>."
        )
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def load_job_description() -> str:
    job_file = INPUT_DIR / "job.txt"
    if not job_file.exists():
        raise FileNotFoundError(f"Job description missing. Create {job_file} and paste the job posting.")
    text = job_file.read_text(encoding="utf-8").strip()
    if not text:
        raise FileNotFoundError(f"{job_file} is empty. Paste the job description into it.")
    return text


def slugify(value: str, fallback: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-").lower()
    return slug or fallback


def resume_to_txt(resume: StructuredResume) -> str:
    lines = []
    c = resume.candidate

    if c.name:
        lines.append(c.name.upper())
    contact = " | ".join(x for x in [c.email, c.phone, c.location] if x)
    if contact:
        lines.append(contact)
    if c.links:
        lines.append(" | ".join(c.links))
    lines.append("")

    def section(title):
        lines.append("")
        lines.append(title)
        lines.append("=" * len(title))

    if resume.summary:
        section("PROFESSIONAL SUMMARY")
        lines.append(resume.summary)

    if resume.skills:
        section("SKILLS")
        lines.append(", ".join(s.name for s in resume.skills))

    if resume.experience:
        section("EXPERIENCE")
        for exp in resume.experience:
            header = exp.title
            if exp.company:
                header += f" - {exp.company}"
            if exp.location:
                header += f", {exp.location}"
            lines.append(header)
            date_range = exp.start_date
            if exp.end_date:
                date_range += f" - {exp.end_date}"
            lines.append(date_range)
            for desc in exp.description:
                lines.append(f"- {desc}")
            if exp.technologies:
                lines.append(f"Technologies: {', '.join(exp.technologies)}")
            lines.append("")

    if resume.projects:
        section("PROJECTS")
        for proj in resume.projects:
            header = proj.name
            if proj.url:
                header += f" - {proj.url}"
            lines.append(header)
            if proj.description:
                lines.append(proj.description)
            if proj.technologies:
                lines.append(f"Technologies: {', '.join(proj.technologies)}")
            lines.append("")

    if resume.education:
        section("EDUCATION")
        for edu in resume.education:
            header = edu.degree
            if edu.institution:
                header += f" - {edu.institution}"
            if edu.location:
                header += f", {edu.location}"
            lines.append(header)
            meta = []
            if edu.graduation_date:
                meta.append(edu.graduation_date)
            if edu.gpa:
                meta.append(f"GPA: {edu.gpa}")
            if meta:
                lines.append(" | ".join(meta))

    if resume.certifications:
        section("CERTIFICATIONS")
        for cert in resume.certifications:
            line = cert.name
            if cert.issuer:
                line += f" - {cert.issuer}"
            if cert.date:
                line += f" ({cert.date})"
            lines.append(line)

    return "\n".join(lines).strip() + "\n"


async def run(resume_arg: str | None) -> None:
    resume_path = pick_resume_path(resume_arg)
    job_text = load_job_description()

    parser = ResumeParserService()
    job_analyzer = JobAnalyzerService()
    matcher = ResumeMatcherService()
    tailor = ResumeTailorService()
    cover_letter_svc = CoverLetterService()
    ats_svc = ATSAnalyzerService()
    pdf_gen = PDFGeneratorService()
    docx_gen = DOCXGeneratorService()

    services = [parser, job_analyzer, matcher, tailor, cover_letter_svc, ats_svc]
    try:
        raw_resume = await parser.extract_text(str(resume_path))
        print(f"[1/6] Parsing master resume: {resume_path.name}")
        structured: StructuredResume = await parser.parse_resume(raw_resume)

        print("[2/6] Analyzing job description")
        title = structured.candidate.name or "Applicant"
        company = "Company"
        m = re.search(r"(?:title|position|role)[:\-]\s*(.+)", job_text[:1500], re.IGNORECASE)
        if m:
            title = m.group(1).strip()
        requirements: JobRequirements = await job_analyzer.analyze_job(title, company, job_text)

        print("[3/6] Matching resume to job requirements")
        match: ResumeMatchResult = await matcher.match_resume(structured, requirements)

        print("[4/6] Tailoring resume (master resume is not modified)")
        tailored: StructuredResume = await tailor.tailor_resume(
            structured, requirements, match, title, company
        )

        print("[5/6] Writing cover letter")
        cover_letter: str = await cover_letter_svc.generate_cover_letter(
            tailored, requirements, match, title, company
        )

        print("[6/6] Scoring ATS compatibility")
        try:
            ats = await ats_svc.analyze_ats(tailored, requirements, match)
            ats_score = ats.overall_score
        except Exception as e:
            print(f"      (ATS scoring skipped: {e})")
            ats_score = None

        job_slug = slugify(title, "job")
        comp_slug = slugify(company, "company")
        out_dir = OUTPUT_DIR / f"{comp_slug}_{job_slug}"
        out_dir.mkdir(parents=True, exist_ok=True)

        resume_pdf = pdf_gen.generate_resume_pdf(tailored, company, title)
        resume_docx = docx_gen.generate_resume_docx(tailored, company, title)
        cl_pdf = pdf_gen.generate_cover_letter_pdf(cover_letter, company, title)

        resume_txt = out_dir / "tailored_resume.txt"
        cl_txt = out_dir / "cover_letter.txt"
        resume_txt.write_text(resume_to_txt(tailored), encoding="utf-8")
        cl_txt.write_text(cover_letter, encoding="utf-8")

        from shutil import copy2
        copy2(resume_pdf, out_dir / "tailored_resume.pdf")
        copy2(resume_docx, out_dir / "tailored_resume.docx")
        copy2(cl_pdf, out_dir / "cover_letter.pdf")

        print(f"\nDone! Output in: {out_dir}")
        for f in sorted(out_dir.iterdir()):
            print(f"  - {f.name}")
        if ats_score is not None:
            print(f"\nATS score: {ats_score:.1f}/100")
            print(f"  Missing keywords: {', '.join(getattr(ats, 'missing_keywords', []) or []) or 'none'}")
    finally:
        for svc in services:
            try:
                await svc.close()
            except Exception:
                pass


def main() -> None:
    ap = argparse.ArgumentParser(description="Tailor resume and write cover letter from input/job.txt")
    ap.add_argument("--resume", help="Path to master resume (default: newest pdf/docx/txt in uploads/)")
    args = ap.parse_args()
    asyncio.run(run(args.resume))


if __name__ == "__main__":
    main()
