# AI Resume Tailor

A production-ready Python application that takes your master resume and a job description, then creates a highly targeted ATS-friendly resume and customized cover letter.

**The master resume is NEVER modified.**

## Features

- **Resume Parsing** - Extract structured data from PDF, DOCX, and TXT resumes
- **Job Analysis** - AI-powered extraction of job requirements and keywords
- **Resume Matching** - Classify requirements as MATCH, PARTIAL_MATCH, or MISSING
- **Resume Tailoring** - Create job-specific resumes while maintaining truthfulness
- **Cover Letter Generation** - Customized cover letters for each application
- **ATS Scoring** - Analyze resume compatibility with Applicant Tracking Systems
- **PDF/DOCX Generation** - Download tailored resumes and cover letters
- **Zero Hallucination** - AI never invents skills, experience, or achievements

## Tech Stack

- Python 3.12+
- FastAPI
- SQLAlchemy (async) + SQLite/PostgreSQL
- Alembic (migrations)
- PyMuPDF (PDF extraction)
- python-docx (DOCX extraction/generation)
- ReportLab (PDF generation)
- Jinja2 (server-rendered UI)
- Pydantic (data validation)

## Setup

```bash
# Clone and enter directory
cd ai-resume-tailor

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Edit .env with your settings
# At minimum, set AI_API_KEY

# Run database migrations
alembic upgrade head

# Start the server
python main.py
```

The app will be available at `http://localhost:8000`.

## AI Provider Configuration

Set in `.env`:

```env
AI_PROVIDER=openrouter    # openrouter, openai, anthropic, local
AI_API_KEY=your-key-here
AI_BASE_URL=https://openrouter.ai/api/v1
AI_MODEL=anthropic/claude-3.5-sonnet
```

### Supported Providers

| Provider | AI_PROVIDER | Base URL |
|----------|------------|----------|
| OpenRouter | `openrouter` | `https://openrouter.ai/api/v1` |
| OpenAI | `openai` | `https://api.openai.com/v1` |
| Anthropic | `anthropic` | `https://api.anthropic.com` |
| Local | `local` | `http://localhost:1234/v1` |

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register user
- `POST /api/auth/login` - Login
- `GET /api/auth/me` - Current user

### Resumes
- `POST /api/resumes/upload` - Upload resume (PDF/DOCX/TXT)
- `GET /api/resumes/` - List resumes
- `GET /api/resumes/{id}` - Get resume detail
- `DELETE /api/resumes/{id}` - Delete resume

### Jobs
- `POST /api/jobs/` - Create job
- `GET /api/jobs/` - List jobs
- `GET /api/jobs/{id}` - Get job detail
- `DELETE /api/jobs/{id}` - Delete job

### Applications
- `POST /api/applications/` - Create application
- `GET /api/applications/` - List applications
- `GET /api/applications/{id}` - Get application detail
- `POST /api/applications/{id}/match` - Match resume to job
- `POST /api/applications/{id}/tailor` - Tailor resume
- `POST /api/applications/{id}/ats` - ATS analysis
- `POST /api/applications/{id}/cover-letter` - Generate cover letter
- `PUT /api/applications/{id}/status` - Update status

### Documents
- `POST /api/applications/{id}/generate-documents` - Generate PDF/DOCX
- `GET /api/applications/{id}/resume/pdf` - Download resume PDF
- `GET /api/applications/{id}/resume/docx` - Download resume DOCX
- `GET /api/applications/{id}/cover-letter/pdf` - Download cover letter PDF

## Project Structure

```
ai-resume-tailor/
├── app/
│   ├── main.py          # FastAPI entry point (in project root)
│   ├── config.py        # Settings from environment
│   ├── database.py      # SQLAlchemy async setup
│   ├── models/          # SQLAlchemy models
│   ├── schemas/         # Pydantic schemas
│   ├── routers/         # API routes
│   ├── services/        # Business logic
│   ├── ai/              # AI provider abstraction
│   └── prompts/         # AI prompt templates
├── templates/           # Jinja2 HTML templates
├── tests/               # pytest tests
├── alembic/             # Database migrations
├── uploads/             # Uploaded resume files
├── generated/           # Generated PDF/DOCX files
├── main.py              # Application entry point
├── requirements.txt
├── .env.example
└── alembic.ini
```

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=app
```

## Database Migrations

```bash
# Generate migration after model changes
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one step
alembic downgrade -1
```

## License

MIT
