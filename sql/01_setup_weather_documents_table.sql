CREATE TABLE IF NOT EXISTS weather_documents (

    id TEXT PRIMARY KEY,

    location TEXT,

    source_type TEXT,

    headline TEXT,

    narrative_text TEXT,

    issued_at TIMESTAMP,

    payload JSONB,

    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

);


CREATE INDEX IF NOT EXISTS idx_weather_documents_location

ON weather_documents(location);