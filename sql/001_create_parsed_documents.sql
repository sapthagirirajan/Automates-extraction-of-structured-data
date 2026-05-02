-- Migration 001: parsed_documents cache table.
-- Run with:
--   psql "$SUPABASE_DB_URL" -f sql/001_create_parsed_documents.sql

CREATE TABLE IF NOT EXISTS parsed_documents (
    id            BIGSERIAL PRIMARY KEY,
    content_hash  CHAR(64)        NOT NULL,
    doc_type      TEXT            NOT NULL CHECK (doc_type IN ('resume', 'jd')),
    raw_text      TEXT            NOT NULL,
    parsed_json   JSONB           NOT NULL,
    model_used    TEXT            NOT NULL,
    created_at    TIMESTAMPTZ     NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS parsed_documents_content_hash_idx
    ON parsed_documents (content_hash);

CREATE INDEX IF NOT EXISTS parsed_documents_doc_type_idx
    ON parsed_documents (doc_type);
