from app.prompts import COVER_LETTER_PROMPT
from app.ai.factory import get_ai_provider
from app.schemas.resume import StructuredResume
from app.schemas.job import JobRequirements
from app.schemas.application import ResumeMatchResult


class CoverLetterService:
    def __init__(self):
        try:
            self.ai_provider = get_ai_provider()
        except ValueError:
            self.ai_provider = None

    async def generate_cover_letter(
        self,
        resume: StructuredResume,
        job_requirements: JobRequirements,
        match_result: ResumeMatchResult,
        job_title: str,
        company: str,
    ) -> str:
        if not self.ai_provider:
            raise ValueError("AI provider not configured. Set AI_API_KEY in .env")
        resume_json = resume.model_dump_json(indent=2)
        job_json = job_requirements.model_dump_json(indent=2)
        match_json = match_result.model_dump_json(indent=2)

        prompt = COVER_LETTER_PROMPT.replace("{{resume_json}}", resume_json)
        prompt = prompt.replace("{{job_requirements_json}}", job_json)
        prompt = prompt.replace("{{match_analysis_json}}", match_json)
        prompt = prompt.replace("{{job_title}}", job_title)
        prompt = prompt.replace("{{company}}", company)

        max_retries = 2
        for attempt in range(max_retries):
            try:
                result = await self.ai_provider.generate(prompt)
                return result.strip()
            except Exception as e:
                if attempt == max_retries - 1:
                    raise ValueError(f"Failed to generate cover letter after {max_retries} attempts: {e}")
                continue

        raise ValueError("Failed to generate cover letter")

    async def close(self):
        if self.ai_provider:
            await self.ai_provider.close()