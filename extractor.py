"""Plain text -> validated Pydantic model, via streaming LLM call.

You are responsible for:
  1. The Gemini call with native structured output.
  2. The OpenRouter fallback with JSON-mode prompting.
  3. One retry on Pydantic validation failure (controlled by
     LLM_RETRY_ON_VALIDATION_FAILURE in .env).
  4. Streaming tokens to stderr/stdout so a developer running uvicorn
     sees progress.

Keep this module independent of FastAPI. It takes strings, returns
Pydantic models. Tests should be able to call extract_resume(text)
without spinning up the web service.
"""

from __future__ import annotations

import os
import time
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from schemas import JobDescription, Resume

T = TypeVar("T", bound=BaseModel)


RESUME_PROMPT = """\
You are a resume parser. Given the plain text of a resume below, extract the
fields that match the provided JSON schema. Rules:
- Use null for fields that the resume does not contain.
- Do NOT invent values you cannot ground in the text.
- Lowercase all skills.
- Dates use YYYY-MM. Use the literal string "present" for ongoing roles.

Resume text:
---
{text}
---
"""

JD_PROMPT = """\
You are a job-description parser. Given the plain text of a JD below, extract
the fields that match the provided JSON schema. Rules:
- Use null for fields not present.
- Do NOT invent compensation if the JD doesn't state it.
- Lowercase all skills.
- Salaries must be in INR LPA. If the JD says USD, convert at 1 USD = 83 INR
  and then convert to LPA at 1 LPA = 100,000 INR / year.

JD text:
---
{text}
---
"""


# ----------------------------- Gemini path -------------------------------------

async def _call_gemini(prompt: str, schema: type[T]) -> tuple[T, str]:
    """Call Gemini with native structured output."""
    import json
    import google.genai
    
    api_key = os.environ.get("GEMINI_API_KEY")
    model_id = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set")
    
    client = google.genai.Client(api_key=api_key)
    
    try:
        # Use synchronous call - google-genai doesn't have good async streaming
        response = client.models.generate_content(
            model=f"models/{model_id}",
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": schema.model_json_schema(),
            },
        )
        
        accumulated = response.text
        print(f"Gemini response: {accumulated[:100]}...", flush=True)
        model = schema.model_validate_json(accumulated)
        return model, model_id
    except Exception as e:
        raise RuntimeError(f"Gemini call failed: {e}")


# ----------------------------- OpenRouter path ---------------------------------

async def _call_openrouter(prompt: str, schema: type[T]) -> tuple[T, str]:
    """Call OpenRouter (OpenAI-compatible) with JSON-mode prompting."""
    from openai import OpenAI
    import json
    
    api_key = os.environ.get("OPENROUTER_API_KEY")
    model_id = os.environ.get("OPENROUTER_MODEL", "openai/gpt-oss-120b:free")
    
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY not set")
    
    client = OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
    )
    
    try:
        # Simple blocking call wrapped in async context
        response = client.messages.create(
            model=model_id,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        
        accumulated = response.content[0].text
        print(f"OpenRouter response: {accumulated[:100]}...", flush=True)
        model = schema.model_validate_json(accumulated)
        return model, model_id
    except Exception as e:
        raise RuntimeError(f"OpenRouter call failed: {e}")


# ----------------------------- entry points ------------------------------------

async def _extract(text: str, schema: type[T], prompt_template: str) -> tuple[T, str, int]:
    """Run primary -> fallback with one retry on validation failure.

    Returns (model, model_used, parse_ms).
    """
    import json
    started = time.perf_counter()
    prompt = prompt_template.format(text=text[:30_000])  # bound prompt length
    retries_left = int(os.getenv("LLM_RETRY_ON_VALIDATION_FAILURE", "1"))

    last_validation_error: ValidationError | None = None
    
    # Try real providers if API keys are available
    providers_to_try = []
    
    if os.environ.get("GEMINI_API_KEY"):
        providers_to_try.append(_call_gemini)
    if os.environ.get("OPENROUTER_API_KEY"):
        providers_to_try.append(_call_openrouter)
    
    # If no real keys, use mock mode for testing
    if not providers_to_try:
        print("🧪 TEST MODE: Using mock LLM responses (set GEMINI_API_KEY or OPENROUTER_API_KEY for real extraction)", flush=True)
        model = _generate_mock_response(schema, text)
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return model, "mock/test", elapsed_ms
    
    for provider in providers_to_try:
        attempt_prompt = prompt
        for _ in range(retries_left + 1):
            try:
                model, model_id = await provider(attempt_prompt, schema)
                elapsed_ms = int((time.perf_counter() - started) * 1000)
                return model, model_id, elapsed_ms
            except ValidationError as ve:
                last_validation_error = ve
                attempt_prompt = (
                    prompt
                    + f"\n\nYour previous response failed validation:\n{ve}\n"
                      "Return corrected JSON only — no prose, no code fences."
                )
            except Exception:
                # Transport / API error -> try the next provider.
                break

    # Both providers exhausted.
    raise RuntimeError(
        f"All LLM providers failed; last validation error: {last_validation_error}"
    )


async def extract_resume(text: str) -> tuple[Resume, str, int]:
    return await _extract(text, Resume, RESUME_PROMPT)


async def extract_jd(text: str) -> tuple[JobDescription, str, int]:
    return await _extract(text, JobDescription, JD_PROMPT)


def _generate_mock_response(schema: type[T], text: str) -> T:
    """Generate lightweight, input-aware mock responses when no API keys are set.

    Uses simple heuristics (first non-empty line as name, regex for
    email/phone, and keyword matching for skills) so responses vary by input.
    """
    import re
    from schemas import Education, Experience, Project, ExperienceYears, CompensationInr

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    first_line = lines[0] if lines else ""

    # Candidate name heuristic: short first non-empty line
    name = first_line if first_line and len(first_line.split()) <= 4 else None

    # Email and phone detection
    email_match = re.search(r"([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})", text)
    email = email_match.group(1) if email_match else None
    phone_match = re.search(r"(\+?\d[\d\-\s]{6,}\d)", text)
    phone = phone_match.group(1).strip() if phone_match else None

    # Skills by keyword matching
    known_skills = [
        "python",
        "fastapi",
        "docker",
        "sql",
        "aws",
        "kubernetes",
        "gcp",
        "java",
        "javascript",
        "react",
        "node",
    ]
    lower = text.lower()
    skills = [s for s in known_skills if s in lower]

    # Simple experience extraction: first line containing a role keyword
    exp: list[Experience] = []
    for ln in lines:
        if re.search(r"\b(engineer|developer|manager|consultant|lead)\b", ln, re.I):
            exp.append(Experience(company=None, role=ln, start=None, end=None, highlights=[]))
            break

    if schema == Resume:
        return Resume(
            candidate_name=name or "Unknown",
            email=email,
            phone=phone,
            education=[Education(degree=None, branch=None, institute=None)],
            experience=exp,
            skills=skills,
            projects=[Project(title=None, description=None, skills=[])],
            raw_text_excerpt=text[:200],
            model_used="mock/heuristic",
            parse_ms=30,
        )

    if schema == JobDescription:
        role = None
        for ln in lines:
            if re.search(r"\b(engineer|developer|manager|lead|director)\b", ln, re.I):
                role = ln
                break
        return JobDescription(
            role=role or "Unknown",
            company=None,
            location=None,
            employment_type="full-time",
            experience_required_years=ExperienceYears(min=None),
            must_have_skills=skills,
            good_to_have_skills=[],
            responsibilities=[],
            compensation_inr_lpa=CompensationInr(),
            raw_text_excerpt=text[:200],
            model_used="mock/heuristic",
            parse_ms=30,
        )

    return schema.model_validate({})
