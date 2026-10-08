import os
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, KeepTogether
from reportlab.lib.colors import HexColor

from app.config import settings
from app.schemas.resume import StructuredResume


class PDFGeneratorService:
    def __init__(self):
        os.makedirs(settings.GENERATED_DIR, exist_ok=True)

    def _resume_story(self, resume: StructuredResume, scale: float) -> list:
        """Build the resume story with compact styles; `scale` shrinks font sizes."""

        def F(base, lf):
            return base * scale, lf * scale

        name_fs, name_ld = F(14, 16)
        contact_fs, contact_ld = F(8, 10)
        section_fs, section_ld = F(10.5, 12)
        body_fs, body_ld = F(8.7, 11)
        job_fs, job_ld = F(9.4, 12)
        meta_fs, meta_ld = F(8, 10)

        styles = getSampleStyleSheet()
        name_style = ParagraphStyle(
            "Name", parent=styles["Title"], fontSize=name_fs, leading=name_ld, spaceAfter=1,
            alignment=TA_CENTER, textColor=HexColor("#1a1a1a"),
        )
        contact_style = ParagraphStyle(
            "Contact", parent=styles["Normal"], fontSize=contact_fs, leading=contact_ld,
            alignment=TA_CENTER, textColor=HexColor("#555555"), spaceAfter=2,
        )
        section_style = ParagraphStyle(
            "Section", parent=styles["Heading2"], fontSize=section_fs, leading=section_ld,
            spaceAfter=2, spaceBefore=5, textColor=HexColor("#1a1a1a"),
        )
        body_style = ParagraphStyle(
            "Body", parent=styles["Normal"], fontSize=body_fs, leading=body_ld,
            textColor=HexColor("#333333"),
        )
        bullet_style = ParagraphStyle(
            "Bullet", parent=body_style, leftIndent=12, bulletIndent=4,
            spaceBefore=0.5, spaceAfter=0.5,
        )
        job_title_style = ParagraphStyle(
            "JobTitle", parent=body_style, fontSize=job_fs, leading=job_ld,
            textColor=HexColor("#1a1a1a"),
        )
        meta_style = ParagraphStyle(
            "Meta", parent=body_style, fontSize=meta_fs, leading=meta_ld,
            textColor=HexColor("#666666"), spaceAfter=1,
        )

        def rule():
            return HRFlowable(width="100%", thickness=0.4, color=HexColor("#cccccc"), spaceBefore=1, spaceAfter=2)

        story = []
        c = resume.candidate

        header = []
        if c.name:
            header.append(Paragraph(c.name, name_style))
        contact_parts = []
        if c.email:
            contact_parts.append(c.email)
        if c.phone:
            contact_parts.append(c.phone)
        if c.location:
            contact_parts.append(c.location)
        if contact_parts:
            header.append(Paragraph(" | ".join(contact_parts), contact_style))
        if c.links:
            header.append(Paragraph(" | ".join(c.links), contact_style))
        story.extend(header)

        if resume.summary:
            story.append(rule())
            story.append(Paragraph("PROFESSIONAL SUMMARY", section_style))
            story.append(Paragraph(resume.summary, body_style))

        if resume.skills:
            skills_text = ", ".join(s.name for s in resume.skills)
            story.append(rule())
            story.append(Paragraph("SKILLS", section_style))
            story.append(Paragraph(skills_text, body_style))

        if resume.experience:
            story.append(rule())
            story.append(Paragraph("EXPERIENCE", section_style))
            for exp in resume.experience:
                title_line = f"<b>{exp.title}</b> - {exp.company}"
                if exp.location:
                    title_line += f", {exp.location}"
                story.append(Paragraph(title_line, job_title_style))
                date_range = exp.start_date
                if exp.end_date:
                    date_range += f" - {exp.end_date}"
                story.append(Paragraph(date_range, meta_style))
                for desc in exp.description:
                    story.append(Paragraph(desc, bullet_style, bulletText="\u2022"))
                if exp.technologies:
                    story.append(Paragraph(
                        "<b>Technologies:</b> " + ", ".join(exp.technologies),
                        meta_style
                    ))
            story.append(Spacer(1, 2))

        if resume.projects:
            story.append(rule())
            story.append(Paragraph("PROJECTS", section_style))
            for proj in resume.projects:
                proj_line = f"<b>{proj.name}</b>"
                if proj.url:
                    proj_line += f" - {proj.url}"
                story.append(Paragraph(proj_line, job_title_style))
                dates = ""
                if proj.start_date:
                    dates = proj.start_date
                    if proj.end_date:
                        dates += f" - {proj.end_date}"
                if dates:
                    story.append(Paragraph(dates, meta_style))
                if proj.description:
                    story.append(Paragraph(proj.description, body_style))
                if proj.technologies:
                    story.append(Paragraph(
                        "<b>Technologies:</b> " + ", ".join(proj.technologies),
                        meta_style
                    ))
            story.append(Spacer(1, 2))

        if resume.education:
            story.append(rule())
            story.append(Paragraph("EDUCATION", section_style))
            for edu in resume.education:
                edu_line = f"<b>{edu.degree}</b> - {edu.institution}"
                if edu.location:
                    edu_line += f", {edu.location}"
                story.append(Paragraph(edu_line, job_title_style))
                meta_parts = []
                if edu.graduation_date:
                    meta_parts.append(edu.graduation_date)
                if edu.gpa:
                    meta_parts.append(f"GPA: {edu.gpa}")
                if meta_parts:
                    story.append(Paragraph(" | ".join(meta_parts), meta_style))

        if resume.certifications:
            story.append(rule())
            story.append(Paragraph("CERTIFICATIONS", section_style))
            for cert in resume.certifications:
                cert_line = f"<b>{cert.name}</b> - {cert.issuer}"
                if cert.date:
                    cert_line += f" ({cert.date})"
                story.append(Paragraph(cert_line, body_style))

        return story

    def _build_pdf(self, filepath: str, story: list, scale: float) -> str:
        doc = SimpleDocTemplate(
            filepath,
            pagesize=letter,
            topMargin=0.35 * inch,
            bottomMargin=0.35 * inch,
            leftMargin=0.55 * inch,
            rightMargin=0.55 * inch,
            title="Tailored Resume",
        )
        doc.build(story)
        return filepath

    @staticmethod
    def _page_count(filepath: str) -> int:
        try:
            import fitz
            with fitz.open(filepath) as d:
                return d.page_count
        except Exception:
            with open(filepath, "rb") as f:
                return f.read().count(b"/Type /Page ") or 1

    def generate_resume_pdf(
        self,
        resume: StructuredResume,
        company: str,
        job_title: str,
    ) -> str:
        safe_company = "".join(c if c.isalnum() else "_" for c in company)
        safe_title = "".join(c if c.isalnum() else "_" for c in job_title)
        filename = f"Resume_{safe_company}_{safe_title}.pdf"
        filepath = os.path.join(settings.GENERATED_DIR, filename)

        # Try progressively smaller font scales until the resume fits on one page.
        for scale in (1.0, 0.95, 0.9, 0.85, 0.8, 0.75, 0.7, 0.65, 0.6, 0.55, 0.5, 0.45):
            story = self._resume_story(resume, scale)
            self._build_pdf(filepath, story, scale)
            if self._page_count(filepath) <= 1:
                break

        return filepath

    def generate_cover_letter_pdf(
        self,
        cover_letter_text: str,
        company: str,
        job_title: str,
    ) -> str:
        safe_company = "".join(c if c.isalnum() else "_" for c in company)
        safe_title = "".join(c if c.isalnum() else "_" for c in job_title)
        filename = f"CoverLetter_{safe_company}_{safe_title}.pdf"
        filepath = os.path.join(settings.GENERATED_DIR, filename)

        doc = SimpleDocTemplate(
            filepath,
            pagesize=letter,
            topMargin=1 * inch,
            bottomMargin=1 * inch,
            leftMargin=1 * inch,
            rightMargin=1 * inch,
        )

        styles = getSampleStyleSheet()
        body_style = ParagraphStyle(
            "CLBody", parent=styles["Normal"], fontSize=11, leading=15,
            textColor=HexColor("#333333"),
        )

        story = []
        paragraphs = cover_letter_text.strip().split("\n\n")
        for para in paragraphs:
            cleaned = para.strip().replace("\n", "<br/>")
            if cleaned:
                story.append(Paragraph(cleaned, body_style))
                story.append(Spacer(1, 12))

        doc.build(story)
        return filepath
