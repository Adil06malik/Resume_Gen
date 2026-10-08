from app.prompts import JOB_ANALYZER_PROMPT
from app.ai.factory import get_ai_provider
from app.schemas.job import JobRequirements
import json


class JobAnalyzerService:
    def __init__(self):
        try:
            self.ai_provider = get_ai_provider()
        except ValueError:
            self.ai_provider = None

    async def analyze_job(
        self,
        title: str,
        company: str,
        description: str,
    ) -> JobRequirements:
        if not self.ai_provider:
            raise ValueError("AI provider not configured. Set AI_API_KEY in .env")
        prompt = JOB_ANALYZER_PROMPT.replace("{{job_title}}", title)
        prompt = prompt.replace("{{company}}", company)
        prompt = prompt.replace("{{job_description}}", description)

        max_retries = 2
        for attempt in range(max_retries):
            try:
                result = await self.ai_provider.generate_json(prompt)
                return JobRequirements(**result)
            except (json.JSONDecodeError, ValueError, TypeError) as e:
                if attempt == max_retries - 1:
                    raise ValueError(f"Failed to analyze job after {max_retries} attempts: {e}")
                continue

        raise ValueError("Failed to analyze job")

    async def close(self):
        if self.ai_provider:
            await self.ai_provider.close()