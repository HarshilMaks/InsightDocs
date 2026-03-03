-- Migration: Add OCR and TTS fields to documents table
-- Date: 2026-03-03

ALTER TABLE documents ADD COLUMN is_scanned BOOLEAN DEFAULT FALSE;
ALTER TABLE documents ADD COLUMN ocr_confidence FLOAT;
ALTER TABLE documents ADD COLUMN has_podcast BOOLEAN DEFAULT FALSE;
ALTER TABLE documents ADD COLUMN podcast_s3_key VARCHAR(500);
ALTER TABLE documents ADD COLUMN podcast_duration FLOAT;
