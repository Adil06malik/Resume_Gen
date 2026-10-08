"""In-memory progress tracking for long-running tailoring jobs.

Progress is keyed by a client-supplied token so the browser can poll while
the synchronous /api/tailor POST is still running on the server.
"""

import time
import threading

_lock = threading.Lock()
_store: dict[str, dict] = {}

STEPS = {
    "started": "Getting started...",
    "parsing": "Parsing your resume...",
    "analyzing": "Analyzing the job description...",
    "matching": "Matching resume to job requirements...",
    "tailoring": "Tailoring your resume for this job...",
    "cover_letter": "Writing your cover letter...",
    "ats": "Scoring ATS compatibility...",
    "generating": "Generating downloadable documents...",
    "done": "Completed!",
}


def create(token: str) -> None:
    with _lock:
        _store[token] = {
            "step": "started",
            "message": STEPS["started"],
            "percent": 5,
            "updated_at": time.time(),
            "error": None,
        }


def set_step(token: str, step: str) -> None:
    if token not in _store:
        return
    if step in STEPS:
        with _lock:
            _store[token]["step"] = step
            _store[token]["message"] = STEPS[step]
            _store[token]["updated_at"] = time.time()


def set_error(token: str, message: str) -> None:
    if token not in _store:
        return
    with _lock:
        _store[token]["error"] = message
        _store[token]["updated_at"] = time.time()


def get(token: str) -> dict | None:
    with _lock:
        return dict(_store.get(token, {}))


def remove(token: str) -> None:
    with _lock:
        _store.pop(token, None)


PROGRESS_BY_STEP = {
    "started": 5,
    "parsing": 10,
    "analyzing": 30,
    "matching": 45,
    "tailoring": 55,
    "cover_letter": 75,
    "ats": 88,
    "generating": 95,
    "done": 100,
}


def percent_for(token: str) -> int:
    info = get(token)
    if not info:
        return 0
    step = info.get("step", "started")
    return PROGRESS_BY_STEP.get(step, 5)


def message_for(token: str) -> str:
    info = get(token)
    if not info:
        return ""
    return info.get("message", "")
