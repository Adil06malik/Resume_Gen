import os

PROMPTS_DIR = os.path.dirname(__file__)


def load_prompt(name: str) -> str:
    path = os.path.join(PROMPTS_DIR, f"{name}.txt")
    with open(path, "r") as f:
        return f.read()


RESUME_PARSER_PROMPT = load_prompt("resume_parser")
JOB_ANALYZER_PROMPT = load_prompt("job_analyzer")
RESUME_MATCHER_PROMPT = load_prompt("resume_matcher")
RESUME_TAILOR_PROMPT = load_prompt("resume_tailor")
COVER_LETTER_PROMPT = load_prompt("cover_letter")
ATS_ANALYZER_PROMPT = load_prompt("ats_analyzer")

__all__ = [
    "load_prompt",
    "RESUME_PARSER_PROMPT",
    "JOB_ANALYZER_PROMPT",
    "RESUME_MATCHER_PROMPT",
    "RESUME_TAILOR_PROMPT",
    "COVER_LETTER_PROMPT",
    "ATS_ANALYZER_PROMPT",
]