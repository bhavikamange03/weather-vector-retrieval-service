# Weather Intelligence Pipeline - Technical Design

This document explains the architectural decisions, data model, and implementation details of the weather vector retrieval system.

---

## 1. Data Source Selection

### Choice: National Weather Service (NWS) API

**API**: `https://api.weather.gov`

### Why NWS?

1. **No API Key Required** - Open, public API with no authentication barriers
2. **High-Quality Unstructured Text** - Rich narrative descriptions perfect for semantic search
3. **Multiple Data Types**:
   - **Weather Alerts**: Detailed warnings with safety instructions (e.g., "Flood Warning")
   - **Forecasts**: Natural language daily/hourly predictions
   - **Forecast Discussions**: Meteorologist narratives explaining weather patterns
4. **Reliable & Authoritative** - Official U.S. government weather data
5. **Free & Rate-Limit Friendly** - No cost, reasonable rate limits for development

### Specific Endpoints Used

```
GET /alerts/active?area={state}
GET /points/{lat},{lon}
GET /gridpoints/{office}/{x},{y}/forecast
GET /offices/{officeId}/discussions/{discussionId}
```

### Data Types Ingested

| Type | Content | Use Case |
|------|---------|----------|
| **alert** | Active weather warnings | "Are there flood warnings?" |
| **forecast** | Daily/hourly predictions | "What's the temperature forecast?" |
| **discussion** | Meteorologist analysis | "Why is the weather changing?" |

---

## 2. Schema Design Decisions

### Database: Lakebase PostgreSQL + pgvector

Chosen for:
- Native vector support (pgvector extension)
- ACID transactions for data consistency
- SQL familiarity and powerful querying
- HNSW index support for fast vector search

### Table 1: `weather_documents`

```sql
CREATE TABLE weather_documents (
    id TEXT PRIMARY KEY,              -- Unique document ID
    location TEXT,                    -- Geographic reference
    source_type TEXT,                 -- 'alert', 'forecast', 'discussion'
    headline TEXT,                    -- Brief title/summary
    narrative_text TEXT,              -- Full content for embedding
    issued_at TIMESTAMP,              -- When issued by NWS
    payload JSONB,                    -- Raw API response (traceability)
    synced_at TIMESTAMP DEFAULT NOW() -- When we ingested it
);
```

**Design Rationale**:
- `source_type` enables filtering (e.g., "show only alerts")
- `narrative_text` is the field we embed and search
- `payload` preserves raw data for debugging
- `issued_at` allows time-based queries
- `location` enables geographic filtering

### Table 2: `weather_embeddings`

```sql
CREATE TABLE weather_embeddings (
    id TEXT PRIMARY KEY,
    document_id TEXT REFERENCES weather_documents(id) ON DELETE CASCADE,
    chunk_index INTEGER,              -- Position in original document
    chunk_text TEXT,                  -- The actual text chunk
    embedding VECTOR(384),            -- 384-dimensional vector
    model_name TEXT,                  -- 'sentence-transformers/all-MiniLM-L6-v2'
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_weather_embeddings_embedding
ON weather_embeddings
USING hnsw (embedding vector_cosine_ops);
```

**Design Rationale**:
- **Chunk-level embeddings**: Better granularity than document-level
- **HNSW index**: 10-100x faster vector search (see HNSW_BENCHMARK.md)
- **Foreign key**: Automatic cleanup when documents deleted
- **chunk_index**: Preserves original document order
- **model_name**: Version tracking for embedding models

---

## 3. Chunking Strategy

### Parameters

```python
CHUNK_SIZE = 800 characters
CHUNK_OVERLAP = 100 characters
```

### Why These Values?

**CHUNK_SIZE = 800**:
- Weather text is typically 100-2000 characters
- 800 chars captures complete thoughts (e.g., full alert description)
- Fits well within embedding model's context window
- Not so large that unrelated concepts get mixed
- Not so small that context is lost

**CHUNK_OVERLAP = 100**:
- Preserves context at chunk boundaries
- Ensures sentences aren't split awkwardly
- ~12.5% overlap balances redundancy vs coverage

### Chunking Example

```
Original: "Heavy rainfall may cause flooding. Rivers rising rapidly. 
           Avoid low-lying areas. Emergency services on standby."

Chunk 1: "Heavy rainfall may cause flooding. Rivers rising rapidly."
Chunk 2:                          "Rivers rising rapidly. Avoid low-lying areas."
Chunk 3:                                            "Avoid low-lying areas. Emergency services..."
                                                     ↑
                                              100-char overlap
```

---

## 4. Embedding Model Selection

### Model: `sentence-transformers/all-MiniLM-L6-v2`

### Why This Model?

| Criteria | Value | Rationale |
|----------|-------|----------|
| **Dimensions** | 384 | Balance between quality and speed |
| **Speed** | ~1000 sentences/sec | Fast enough for real-time queries |
| **Quality** | 0.86 cosine similarity | Strong semantic understanding |
| **Size** | 80 MB | Lightweight, easy to deploy |
| **License** | Apache 2.0 | Commercial use allowed |

### Alternatives Considered

- **all-mpnet-base-v2** (768-d): Higher quality but 2x slower
- **all-distilroberta-v1** (768-d): Good quality but larger
- **OpenAI text-embedding-3-small**: Requires API key & costs money

### Consistency Principle

⚠️ **Critical**: Same model used for:
1. Document embedding (during ingestion)
2. Query embedding (during search)

Mismatched models break semantic similarity!

---

## 5. End-to-End Pipeline

### Pipeline Flow

```
┌──────────────────────────────────────────────────────────┐
│  Step 1: Fetch Weather Data                             │
│  Source: NWS API → weather_client.py                     │
│  Output: Raw JSON documents                              │
└────────────────┬─────────────────────────────────────────┘
                 ↓
┌──────────────────────────────────────────────────────────┐
│  Step 2: Normalize & Store                               │
│  Process: weather_service.py                             │
│  Output: weather_documents table populated               │
└────────────────┬─────────────────────────────────────────┘
                 ↓
┌──────────────────────────────────────────────────────────┐
│  Step 3: Chunk & Embed                                   │
│  Process: ingest_weather_embeddings.py                   │
│  Output: weather_embeddings table populated              │
│          HNSW index built                                │
└────────────────┬─────────────────────────────────────────┘
                 ↓
┌──────────────────────────────────────────────────────────┐
│  Step 4: Search                                          │
│  Interface: Flask API + Web UI                           │
│  Process: Query → Embed → HNSW Search → Results         │
└──────────────────────────────────────────────────────────┘
```

### Running the Pipeline

#### Option 1: Automated (Recommended)

```bash
# Deploy scheduled job (runs every 6 hours)
databricks bundle deploy

# Trigger immediate run
databricks jobs run-now --job-name "Weather Data Ingestion - Every 6 Hours"
```

The job handles Steps 1-3 automatically.

#### Option 2: Manual Step-by-Step

**Step 1 & 2: Fetch and Store Documents**

```bash
# Via API
curl -X POST http://localhost:5000/weather/sync \
  -H "Content-Type: application/json" \
  -d '{
    "locations": [
      {"name": "Chicago", "lat": 41.8781, "lon": -87.6298, "state": "IL"}
    ],
    "limit": 50
  }'

# Or via Python
from services.weather_service import WeatherService
ws = WeatherService()
ws.fetch_and_store_weather_data()
```

Verify:
```sql
SELECT source_type, COUNT(*) FROM weather_documents GROUP BY source_type;
```

**Step 3: Generate Embeddings**

```bash
# Run the notebook
python notebooks/ingest_weather_embeddings.py
```

Verify:
```sql
SELECT COUNT(*) FROM weather_embeddings;
SELECT COUNT(*) FROM pg_indexes WHERE indexname = 'idx_weather_embeddings_embedding';
```

**Step 4: Search**

```bash
# Via Web UI
open http://localhost:5000/weather/search

# Or via API
curl -X POST http://localhost:5000/weather/search \
  -H "Content-Type: application/json" \
  -d '{"query": "flood warnings near rivers", "source_types": ["alert"]}'
```

### Data Freshness

With the scheduled job:
- Data refreshes every 6 hours
- Embeddings auto-generated on new data
- HNSW index auto-updated
- Maximum staleness: 6 hours

---

## 6. Search Implementation

### Query Process

```python
# 1. Convert query to vector
query_embedding = model.encode("flood warnings near rivers")

# 2. Search with HNSW index
SQL: """
SELECT 
    d.location,
    d.headline,
    e.chunk_text,
    1 - (e.embedding <=> %s::vector) AS similarity
FROM weather_embeddings e
JOIN weather_documents d ON e.document_id = d.id
WHERE d.source_type = ANY(%s)  -- Optional filter
ORDER BY e.embedding <=> %s::vector
LIMIT 5
"""

# 3. Return ranked results
```

### Performance

- **Without HNSW**: 50-500ms per query (sequential scan)
- **With HNSW**: 1-10ms per query (graph traversal)
- **Speedup**: 10-100x faster 🚀

See `HNSW_BENCHMARK.md` for detailed benchmarks.

---

## 7. Known Limitations

### Current Limitations

1. **Geographic Coverage**
   - Currently fetches from a single forecast office
   - Need to manually specify lat/lon for new locations
   - **Improvement**: Add geocoding API (Nominatim/Google) to auto-resolve city names

2. **Data Source**
   - Only NWS (US-only weather)
   - **Improvement**: Add OpenWeatherMap, Weather.com, international sources

3. **No Query Expansion**
   - User must phrase query well
   - **Improvement**: Add query rewriting, synonym expansion

4. **No Result Re-ranking**
   - Simple cosine similarity only
   - **Improvement**: Add cross-encoder re-ranking for top results

5. **No LLM Summarization**
   - Returns raw text chunks
   - **Improvement**: Use LLM to synthesize retrieved chunks into natural answer

6. **Chunking is Fixed**
   - 800-char chunks for all document types
   - **Improvement**: Adaptive chunking based on document structure

7. **Single Embedding Model**
   - Locked to MiniLM-L6-v2
   - **Improvement**: Support model swapping, compare embeddings

### Edge Cases

- **Empty Queries**: Returns error (should return popular/recent)
- **Very Long Queries**: Truncated to model limit (should chunk query)
- **No Results**: Returns empty array (should suggest alternatives)
- **Duplicate Documents**: Not deduplicated (should hash and skip)

---

## 8. Future Improvements

### Priority 1: Query Experience

- [ ] **Hybrid Search**: Combine vector search + BM25 keyword search
- [ ] **Query Suggestions**: "Did you mean..." for typos
- [ ] **Faceted Search**: Filter by date, location, severity
- [ ] **Result Highlighting**: Show why each result matched

### Priority 2: Data Quality

- [ ] **Deduplication**: Hash-based duplicate detection
- [ ] **Data Validation**: Check for malformed/missing fields
- [ ] **Historical Data**: Archive old forecasts for trends
- [ ] **Multi-region**: Expand beyond single forecast office

### Priority 3: Performance

- [ ] **Caching**: Cache frequent queries
- [ ] **Async Ingestion**: Non-blocking pipeline
- [ ] **Batch Embedding**: Process multiple docs at once
- [ ] **Index Optimization**: Tune HNSW parameters (m, ef_construction)

### Priority 4: Intelligence

- [ ] **RAG Integration**: Add LLM for natural language answers
- [ ] **Question Answering**: "Will it rain tomorrow?" → Yes/No + evidence
- [ ] **Alerting**: Notify on severe weather matching user criteria
- [ ] **Trend Analysis**: "Is flooding becoming more common?"

---

## 9. Testing & Validation

### Data Quality Tests

```sql
-- Check for null embeddings
SELECT COUNT(*) FROM weather_embeddings WHERE embedding IS NULL;

-- Check embedding dimensions
SELECT DISTINCT array_length(embedding::float[], 1) FROM weather_embeddings;

-- Check for orphaned embeddings
SELECT COUNT(*) FROM weather_embeddings e
WHERE NOT EXISTS (SELECT 1 FROM weather_documents d WHERE d.id = e.document_id);
```

### Search Quality Tests

```python
test_queries = [
    ("flooding near rivers", ["flood", "river"]),
    ("high temperature", ["heat", "hot", "warm"]),
    ("severe thunderstorm", ["thunder", "lightning", "storm"])
]

for query, expected_terms in test_queries:
    results = search(query)
    assert any(term in result['text'].lower() for term in expected_terms)
```

### Performance Tests

- Run `notebooks/hnsw_index_benchmark.py`
- Target: <10ms average query latency
- Target: >0.8 similarity for known matches

---

## 10. Architecture Diagram

```
                 ┌─────────────────────────────┐
                 │   Scheduled Job (6h)        │
                 │   Databricks Workflow       │
                 └─────────────┬───────────────┘
                               │
                               ↓
              ┌────────────────────────────────────┐
              │   NWS API                          │
              │   - Alerts                         │
              │   - Forecasts                      │
              │   - Discussions                    │
              └────────────┬───────────────────────┘
                           │
                           ↓
              ┌────────────────────────────────────┐
              │   weather_client.py                │
              │   Normalize JSON → Documents       │
              └────────────┬───────────────────────┘
                           │
                           ↓
              ┌────────────────────────────────────┐
              │   Lakebase PostgreSQL              │
              │   ┌──────────────────────────┐     │
              │   │  weather_documents       │     │
              │   │  (id, location, text...) │     │
              │   └──────────────────────────┘     │
              └────────────┬───────────────────────┘
                           │
                           ↓
              ┌────────────────────────────────────┐
              │   Embedding Pipeline               │
              │   sentence-transformers MiniLM     │
              │   Chunk (800) + Overlap (100)      │
              └────────────┬───────────────────────┘
                           │
                           ↓
              ┌────────────────────────────────────┐
              │   weather_embeddings               │
              │   ┌──────────────────────────┐     │
              │   │  embedding VECTOR(384)   │     │
              │   │  + HNSW index            │     │
              │   └──────────────────────────┘     │
              └────────────┬───────────────────────┘
                           │
                           ↓
              ┌────────────────────────────────────┐
              │   Flask API + Web UI               │
              │   /weather/search                  │
              │   Query → Embed → HNSW → Results   │
              └────────────────────────────────────┘
```

---

## Summary

This pipeline demonstrates:

✅ **Real-world data ingestion** from public APIs  
✅ **Production schema design** with proper indexing  
✅ **Semantic search** using vector embeddings  
✅ **Performance optimization** with HNSW (10-100x speedup)  
✅ **Automated workflows** via Databricks Jobs  
✅ **End-to-end RAG pipeline** ready for LLM integration  

For implementation details, see:
- `README.md` - Main documentation
- `QUICKSTART.md` - 5-minute setup guide
- `HNSW_BENCHMARK.md` - Performance analysis
- `resources/README.md` - Job configuration details