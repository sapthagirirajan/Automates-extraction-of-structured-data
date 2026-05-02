"""FastAPI service on :8005. Document intelligence pipeline."""
from __future__ import annotations
import hashlib, json, os, sqlite3
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Request, Response, UploadFile
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from extractor import extract_jd, extract_resume
from parser import parse
from schemas import JobDescription, Resume

try:
    import psycopg
    USE_POSTGRES = True
except ImportError:
    USE_POSTGRES = False

load_dotenv()
DB_URL = os.environ.get("SUPABASE_DB_URL", "")
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_MB", "5")) * 1024 * 1024
SQLITE_DB = "parsed_documents.db"

def _get_conn():
    return psycopg.connect(DB_URL) if USE_POSTGRES else sqlite3.connect(SQLITE_DB)

def _cache_lookup(content_hash: str):
    conn = _get_conn()
    try:
        if USE_POSTGRES:
            with conn.cursor() as cur:
                cur.execute("SELECT parsed_json, model_used FROM parsed_documents WHERE content_hash = %s", (content_hash,))
                row = cur.fetchone()
                return {"parsed_json": row[0], "model_used": row[1]} if row else None
        else:
            cur = conn.cursor()
            cur.execute("SELECT parsed_json, model_used FROM parsed_documents WHERE content_hash = ?", (content_hash,))
            row = cur.fetchone()
            if row:
                pj = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                return {"parsed_json": pj, "model_used": row[1]}
    finally:
        conn.close()
    return None

def _cache_insert(content_hash: str, doc_type: str, raw_text: str, parsed_json: dict, model_used: str):
    conn = _get_conn()
    try:
        if USE_POSTGRES:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO parsed_documents (content_hash, doc_type, raw_text, parsed_json, model_used) VALUES (%s,%s,%s,%s,%s) ON CONFLICT (content_hash) DO NOTHING", (content_hash, doc_type, raw_text, json.dumps(parsed_json), model_used))
            conn.commit()
        else:
            cur = conn.cursor()
            cur.execute("INSERT OR IGNORE INTO parsed_documents (content_hash, doc_type, raw_text, parsed_json, model_used) VALUES (?,?,?,?,?)", (content_hash, doc_type, raw_text, json.dumps(parsed_json), model_used))
            conn.commit()
    finally:
        conn.close()

def _is_english(text: str) -> bool:
    try:
        from langdetect import detect
        return detect(text) == "en"
    except:
        return (sum(1 for c in text if ord(c) < 128) / len(text) >= 0.9) if text else True

def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

@asynccontextmanager
async def lifespan(app: FastAPI):
    conn = _get_conn()
    try:
        if USE_POSTGRES:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.execute("CREATE TABLE IF NOT EXISTS parsed_documents (id BIGSERIAL PRIMARY KEY, content_hash CHAR(64) NOT NULL, doc_type TEXT NOT NULL, raw_text TEXT NOT NULL, parsed_json JSONB NOT NULL, model_used TEXT NOT NULL, created_at TIMESTAMPTZ DEFAULT now()); CREATE UNIQUE INDEX IF NOT EXISTS idx_hash ON parsed_documents (content_hash);")
            conn.commit()
        else:
            cur = conn.cursor()
            cur.execute("CREATE TABLE IF NOT EXISTS parsed_documents (id INTEGER PRIMARY KEY, content_hash TEXT UNIQUE NOT NULL, doc_type TEXT NOT NULL, raw_text TEXT NOT NULL, parsed_json TEXT NOT NULL, model_used TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);")
            conn.commit()
    finally:
        conn.close()
    yield

app = FastAPI(title="Document Intelligence", lifespan=lifespan)

@app.post("/parse/resume")
async def parse_resume(response: Response, file: UploadFile = File(...)):
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "file too large")
    content_hash = _sha256(data)
    cached = _cache_lookup(content_hash)
    if cached:
        response.headers["X-Cache"] = "HIT"
        return cached["parsed_json"]
    try:
        _fmt, text = parse(data)
    except ValueError as e:
        raise HTTPException(415, str(e))
    if not text.strip():
        raise HTTPException(415, "empty document")
    if not _is_english(text):
        raise HTTPException(415, "only English documents")
    try:
        resume, model_used, parse_ms = await extract_resume(text)
    except ValidationError as ve:
        return JSONResponse(status_code=422, content={"detail": json.loads(ve.json())})
    except RuntimeError as re:
        raise HTTPException(502, f"LLM failed: {re}")
    resume.raw_text_excerpt = text[:500]
    resume.model_used = model_used
    resume.parse_ms = parse_ms
    _cache_insert(content_hash, "resume", text, resume.model_dump(), model_used)
    response.headers["X-Cache"] = "MISS"
    return resume.model_dump()

@app.post("/parse/jd")
async def parse_jd(request: Request, response: Response):
    ct = request.headers.get("content-type", "").lower()
    text = None
    if "application/json" in ct:
        try:
            body = await request.json()
            text = body.get("text", "").strip()
        except:
            raise HTTPException(400, "invalid JSON")
        if not text:
            raise HTTPException(422, "text cannot be empty")
        content_hash = _sha256(text.encode("utf-8"))
    elif "multipart/form-data" in ct:
        form = await request.form()
        file = form.get("file")
        if not file:
            raise HTTPException(400, "file required")
        data = await file.read()
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(413, "file too large")
        content_hash = _sha256(data)
        try:
            _fmt, text = parse(data)
        except ValueError as e:
            raise HTTPException(415, str(e))
        if not text.strip():
            raise HTTPException(415, "empty document")
    else:
        raise HTTPException(415, "unsupported content-type")
    if not _is_english(text):
        raise HTTPException(415, "only English documents")
    cached = _cache_lookup(content_hash)
    if cached:
        response.headers["X-Cache"] = "HIT"
        return cached["parsed_json"]
    try:
        jd, model_used, parse_ms = await extract_jd(text)
    except ValidationError as ve:
        return JSONResponse(status_code=422, content={"detail": json.loads(ve.json())})
    except RuntimeError as re:
        raise HTTPException(502, f"LLM failed: {re}")
    jd.raw_text_excerpt = text[:500]
    jd.model_used = model_used
    jd.parse_ms = parse_ms
    _cache_insert(content_hash, "jd", text, jd.model_dump(), model_used)
    response.headers["X-Cache"] = "MISS"
    return jd.model_dump()

@app.get("/healthz")
def healthz():
    return {"ok": True}
