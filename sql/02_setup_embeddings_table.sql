DROP TABLE IF EXISTS weather_embeddings;


CREATE TABLE weather_embeddings (

    id TEXT PRIMARY KEY,

    document_id TEXT REFERENCES weather_documents(id)
        ON DELETE CASCADE,

    chunk_index INTEGER,

    chunk_text TEXT,

    embedding VECTOR(384),

    model_name TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

);


CREATE INDEX idx_weather_embeddings_embedding

ON weather_embeddings

USING hnsw (embedding vector_cosine_ops);