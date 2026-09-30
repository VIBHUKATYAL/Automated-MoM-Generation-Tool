-- Disable RLS temporarily or set up secure policies if required by client
-- CREATE TABLE
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS meetings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT,
    meeting_date TIMESTAMPTZ,
    participants JSONB,
    original_transcript TEXT,
    processed_transcript TEXT,
    summary TEXT,
    key_points JSONB,
    decisions JSONB,
    action_items JSONB,
    next_meeting_scheduled TEXT,
    
    -- Processing state for background jobs
    processing_status TEXT DEFAULT 'queued',
    error_message TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Trigger for updated_at
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_meetings_modtime ON meetings;

CREATE TRIGGER update_meetings_modtime
BEFORE UPDATE ON meetings
FOR EACH ROW EXECUTE PROCEDURE update_modified_column();
