from app.prompts import ATS_ANALYZER_PROMPT
from app.ai.factory import get_ai_provider
from app.schemas.resume import StructuredResume
from app.schemas.job import JobRequirements
from app.schemas.application import ResumeMatchResult, ATSScore
import json


class ATSAnalyzerService:
    def __init__(self):
        try:
            self.ai_provider = get_ai_provider()
        except ValueError:
            self.ai_provider = None

    async def analyze_ats(
        self,
        tailored_resume: StructuredResume,
        job_requirements: JobRequirements,
        match_result: ResumeMatchResult,
    ) -> ATSScore:
        if not self.ai_provider:
            raise ValueError("AI provider not configured. Set AI_API_KEY in .env")
        resume_json = tailored_resume.model_dump_json(indent=2)
        job_json = job_requirements.model_dump_json(indent=2)
        match_json = match_result.model_dump_json(indent=2)

        prompt = ATS_ANALYZER_PROMPT.replace("{{tailored_resume_json}}", resume_json)
        prompt = prompt.replace("{{job_requirements_json}}", job_json)
        prompt = prompt.replace("{{match_analysis_json}}", match_json)

        max_retries = 2
        for attempt in range(max_retries):
            try:
                result = await self.ai_provider.generate_json(prompt)
                return ATSScore(**result)
            except (json.JSONDecodeError, ValueError, TypeError) as e:
                if attempt == max_retries - 1:
                    raise ValueError(f"Failed to analyze ATS after {max_retries} attempts: {e}")
                continue

        raise ValueError("Failed to analyze ATS")

    async def close(self):
        if self.ai_provider:
            await self.ai_provider.close()