import re
import asyncio
from pathlib import Path

from app.config import settings
from app.services import progress as progress_tracker
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

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def slugify(value: str, fallback: str = "job") -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", value or "").strip("-").lower()
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


def extract_job_meta(description: str, default_title: str, default_company: str):
    title = default_title or "Applicant"
    company = default_company or "Company"
    m = re.search(r"(?:title|position|role|job)\s*[:\-]\s*(.+)", description[:1500], re.IGNORECASE)
    if m:
        title = m.group(1).strip()
    m = re.search(r"company\s*[:\-]\s*(.+)", description[:1500], re.IGNORECASE)
    if m:
        company = m.group(1).strip()
    return title, company


class TailorPipeline:
    async def run(
        self,
        resume_file_path: str,
        job_title: str,
        company: str,
        job_description: str,
        out_dir: str,
        progress_token: str = None,
    ):
        def set_progress(step):
            if progress_token:
                progress_tracker.set_step(progress_token, step)

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
            set_progress("parsing")
            raw_resume = await parser.extract_text(resume_file_path)
            structured: StructuredResume = await parser.parse_resume(raw_resume)

            title, company = extract_job_meta(job_description, job_title, company)
            set_progress("analyzing")
            requirements: JobRequirements = await job_analyzer.analyze_job(title, company, job_description)
            set_progress("matching")
            match: ResumeMatchResult = await matcher.match_resume(structured, requirements)

            set_progress("tailoring")
            tailored: StructuredResume = await tailor.tailor_resume(
                structured, requirements, match, title, company
            )

            set_progress("cover_letter")
            cover_letter: str = await cover_letter_svc.generate_cover_letter(
                tailored, requirements, match, title, company
            )

            set_progress("ats")
            ats = None
            try:
                ats = await ats_svc.analyze_ats(tailored, requirements, match)
            except Exception:
                pass

            set_progress("generating")
            Path(out_dir).mkdir(parents=True, exist_ok=True)

            resume_pdf = pdf_gen.generate_resume_pdf(tailored, company, title)
            resume_docx = docx_gen.generate_resume_docx(tailored, company, title)
            cl_pdf = pdf_gen.generate_cover_letter_pdf(cover_letter, company, title)

            from shutil import copy2
            resume_pdf_dest = str(Path(out_dir) / "tailored_resume.pdf")
            resume_docx_dest = str(Path(out_dir) / "tailored_resume.docx")
            cl_pdf_dest = str(Path(out_dir) / "cover_letter.pdf")
            resume_txt_dest = str(Path(out_dir) / "tailored_resume.txt")
            cl_txt_dest = str(Path(out_dir) / "cover_letter.txt")

            copy2(resume_pdf, resume_pdf_dest)
            copy2(resume_docx, resume_docx_dest)
            copy2(cl_pdf, cl_pdf_dest)
            Path(resume_txt_dest).write_text(resume_to_txt(tailored), encoding="utf-8")
            Path(cl_txt_dest).write_text(cover_letter, encoding="utf-8")

            set_progress("done")
            return {
                "job_title": title,
                "company": company,
                "original_resume": structured.model_dump(),
                "tailored_resume": tailored.model_dump(),
                "ats_score": ats.overall_score if ats else None,
                "ats": ats.model_dump() if ats else None,
                "match": match.model_dump(),
                "missing_keywords": ats.missing_keywords if ats else [],
                "files": {
                    "resume_pdf": resume_pdf_dest,
                    "resume_docx": resume_docx_dest,
                    "resume_txt": resume_txt_dest,
                    "cover_letter_pdf": cl_pdf_dest,
                    "cover_letter_txt": cl_txt_dest,
                },
            }
        except Exception as e:
            if progress_token:
                progress_tracker.set_error(progress_token, str(e))
            raise
        finally:
            for svc in services:
                try:
                    await svc.close()
                except Exception:
                    pass
