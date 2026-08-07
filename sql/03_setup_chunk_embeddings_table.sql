CREATE TABLE IF NOT EXISTS weather_chunk_embeddings (

    id SERIAL PRIMARY KEY,

    document_id TEXT REFERENCES weather_documents(id)
        ON DELETE CASCADE,

    chunk_index INTEGER,

    chunk_text TEXT,

    embedding VECTOR(384),

    model_name TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(document_id, chunk_index)

);


CREATE INDEX IF NOT EXISTS idx_weather_chunk_embeddings_embedding

ON weather_chunk_embeddings

USING hnsw (embedding vector_cosine_ops);