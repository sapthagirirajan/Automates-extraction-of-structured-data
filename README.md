# 39 — Document Intelligence FastAPI (`:8005`)

Scaffold for Milestone 9. **You** fill in the TODOs.

## Setup

```bash
python -m venv venv
venv\Scripts\activate            # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env             # then fill in the keys
psql "$SUPABASE_DB_URL" -f sql/001_create_parsed_documents.sql
```

## Run

```bash
uvicorn main:app --reload --port 8005
```

## Verify

```bash
python verify.py
```

`verify.py` should pass before you call this milestone done. The five assertions it must make are listed in `38 - Background and Approach.md`.

## Files

| File | What you do |
|------|-------------|
| `schemas.py` | **Already complete.** Pydantic models for `Resume`, `JobDescription`, `ParsedDocumentRow`. Read it first. |
| `parser.py` | **TODOs.** Implement `parse_pdf`, `parse_docx`, `detect_format`. |
| `extractor.py` | **TODOs.** Implement `extract_resume` and `extract_jd` against Gemini → OpenRouter fallback, streaming. |
| `main.py` | **TODOs.** Wire up `/parse/resume` and `/parse/jd`, including SHA-256 idempotency cache. |
| `verify.py` | **Empty.** Fill in five assertions. |
| `sql/001_create_parsed_documents.sql` | **Already complete.** Migration for the cache table. |

## Trade-off you must document

In a 5-line section at the bottom of this README, write the one trade-off you made and why. Examples:

- "I chose `pdfplumber` over `PyMuPDF` because… though I lose… "
- "I cache by SHA-256 of the bytes, not the parsed text, because… though this means… "
- "I retry the LLM **once** on validation failure, not twice, because… "

(Replace this section with yours before submitting.)

## Trade-off: Cache by Content Hash

I cache by SHA-256 of the raw bytes (for file uploads) or text (for JSON input) rather than by parsed content, because this ensures idempotency: two uploads of the same PDF always get the same cache result, eliminating re-parsing overhead and deterministic LLM responses. However, this means minor formatting changes (e.g., a rebuilt PDF with identical content) require re-parsing—a worthwhile trade-off for determinism and a simple cache key.
