import os
import pytest
from app.schemas.resume import (
    StructuredResume, CandidateInfo, Skill, Experience, Project, Education, Certification,
)
from app.services.pdf_generator import PDFGeneratorService
from app.services.docx_generator import DOCXGeneratorService


@pytest.fixture
def sample_resume():
    return StructuredResume(
        candidate=CandidateInfo(
            name="John Doe",
            email="john@example.com",
            phone="555-0100",
            location="New York, NY",
            links=["linkedin.com/in/johndoe", "github.com/johndoe"],
        ),
        summary="Experienced software engineer with 5+ years in web development.",
        skills=[
            Skill(name="Python", category="Programming Languages"),
            Skill(name="FastAPI", category="Frameworks"),
            Skill(name="PostgreSQL", category="Databases"),
        ],
        experience=[
            Experience(
                title="Senior Developer",
                company="Tech Corp",
                location="New York, NY",
                start_date="2020-01",
                end_date="Present",
                description=[
                    "Led development of microservices architecture",
                    "Improved API response time by 40%",
                ],
                technologies=["Python", "FastAPI", "PostgreSQL"],
            ),
        ],
        projects=[
            Project(
                name="Open Source Tool",
                description="A tool for automating deployments.",
                technologies=["Python", "Docker"],
                url="github.com/johndoe/tool",
            ),
        ],
        education=[
            Education(
                degree="B.S. Computer Science",
                institution="NYU",
                location="New York, NY",
                graduation_date="2018",
                gpa="3.8",
            ),
        ],
        certifications=[
            Certification(name="AWS Solutions Architect", issuer="Amazon", date="2022"),
        ],
    )


def test_generate_resume_pdf(sample_resume):
    gen = PDFGeneratorService()
    filepath = gen.generate_resume_pdf(sample_resume, "Acme Corp", "Backend Engineer")
    assert os.path.exists(filepath)
    assert filepath.endswith(".pdf")
    assert os.path.getsize(filepath) > 0
    assert "Acme_Corp" in filepath
    assert "Backend_Engineer" in filepath
    os.remove(filepath)


def test_generate_cover_letter_pdf(sample_resume):
    gen = PDFGeneratorService()
    cover_letter = (
        "Dear Hiring Manager,\n\n"
        "I am writing to express my interest in the Backend Engineer position at Acme Corp.\n\n"
        "With 5 years of experience in software engineering, I believe I would be a great fit.\n\n"
        "Sincerely,\nJohn Doe"
    )
    filepath = gen.generate_cover_letter_pdf(cover_letter, "Acme Corp", "Backend Engineer")
    assert os.path.exists(filepath)
    assert filepath.endswith(".pdf")
    assert os.path.getsize(filepath) > 0
    os.remove(filepath)


def test_generate_resume_docx(sample_resume):
    gen = DOCXGeneratorService()
    filepath = gen.generate_resume_docx(sample_resume, "Acme Corp", "Backend Engineer")
    assert os.path.exists(filepath)
    assert filepath.endswith(".docx")
    assert os.path.getsize(filepath) > 0
    assert "Acme_Corp" in filepath
    assert "Backend_Engineer" in filepath
    os.remove(filepath)


def test_generate_resume_pdf_special_characters(sample_resume):
    gen = PDFGeneratorService()
    filepath = gen.generate_resume_pdf(sample_resume, "O'Brien & Associates", "Sr. Engineer")
    assert os.path.exists(filepath)
    assert os.path.getsize(filepath) > 0
    os.remove(filepath)


def test_generate_resume_docx_special_characters(sample_resume):
    gen = DOCXGeneratorService()
    filepath = gen.generate_resume_docx(sample_resume, "O'Brien & Associates", "Sr. Engineer")
    assert os.path.exists(filepath)
    assert os.path.getsize(filepath) > 0
    os.remove(filepath)


def test_generate_documents_empty_resume():
    resume = StructuredResume()
    pdf_gen = PDFGeneratorService()
    docx_gen = DOCXGeneratorService()

    pdf_path = pdf_gen.generate_resume_pdf(resume, "TestCo", "Dev")
    assert os.path.exists(pdf_path)
    os.remove(pdf_path)

    docx_path = docx_gen.generate_resume_docx(resume, "TestCo", "Dev")
    assert os.path.exists(docx_path)
    os.remove(docx_path)
