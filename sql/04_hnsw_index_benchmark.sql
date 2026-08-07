/*
=====================================================
HNSW Index Benchmark Reference Guide
=====================================================

This file documents HNSW index usage and benchmarking.
Use the Python notebook (hnsw_index_benchmark.py) to run
the actual benchmark.

HNSW (Hierarchical Navigable Small World) provides:
  - 10-100x faster vector similarity queries
  - Near-perfect recall (>99%)
  - Scalability to millions of vectors

=====================================================
*/

-- -----------------------------------------------------
-- HNSW Index Creation
-- -----------------------------------------------------

/*
Syntax for creating HNSW index:

CREATE INDEX idx_weather_embeddings_embedding
ON weather_embeddings
USING hnsw (embedding vector_cosine_ops);

Distance operators:
  - vector_cosine_ops: Cosine similarity (1 - cosine distance)
  - vector_l2_ops: Euclidean distance (L2)
  - vector_ip_ops: Inner product (dot product)
*/

-- -----------------------------------------------------
-- Performance Comparison Query
-- -----------------------------------------------------

/*
Example vector similarity query:

SELECT
    document_id,
    chunk_text,
    1 - (embedding <=> %s::vector) AS similarity
FROM weather_embeddings
ORDER BY embedding <=> %s::vector
LIMIT 5;

Without HNSW index:
  - Uses sequential scan
  - Execution time: 50-500ms
  - Scales linearly with data size

With HNSW index:
  - Uses index scan
  - Execution time: 1-10ms
  - Speedup: 10-100x faster!
*/

-- -----------------------------------------------------
-- Query Plan Analysis
-- -----------------------------------------------------

/*
Use EXPLAIN ANALYZE to see query execution:

EXPLAIN ANALYZE
SELECT ...

Without index, look for:
  -> Seq Scan on weather_embeddings

With index, look for:
  -> Index Scan using idx_weather_embeddings_embedding
*/

-- -----------------------------------------------------
-- Index Statistics
-- -----------------------------------------------------

-- Check index and table sizes
SELECT
    pg_size_pretty(pg_relation_size('idx_weather_embeddings_embedding')) AS index_size,
    pg_size_pretty(pg_relation_size('weather_embeddings')) AS table_size;

-- Index usage statistics
SELECT
    indexrelname,
    idx_scan AS scans,
    idx_tup_read AS tuples_read,
    idx_tup_fetch AS tuples_fetched
FROM pg_stat_user_indexes
WHERE indexrelname = 'idx_weather_embeddings_embedding';

-- -----------------------------------------------------
-- Advanced: Tuning Parameters
-- -----------------------------------------------------

/*
Index creation parameters (optional):

CREATE INDEX ... WITH (m = 16, ef_construction = 64);

Parameters:
  - m: Connections per layer
    * Default: 16
    * Range: 4-64
    * Higher = better recall, slower build
  
  - ef_construction: Candidate list size during build
    * Default: 64
    * Range: 16-512
    * Higher = better recall, slower build

Query-time parameter:

SET hnsw.ef_search = 100;

Parameter:
  - ef_search: Candidate list size during search
    * Default: 40
    * Range: 10-1000
    * Higher = better recall, slower queries

Recommended settings:
  Production: m=16, ef_construction=64, ef_search=40-100
  Development: m=8, ef_construction=32, ef_search=20-40
*/

-- -----------------------------------------------------
-- Benchmark Results Reference
-- -----------------------------------------------------

/*
Typical benchmark results:

Dataset size: 1,000 vectors
  Without index: ~50ms per query
  With index:    ~5ms per query
  Speedup:       10x

Dataset size: 10,000 vectors
  Without index: ~200ms per query
  With index:    ~8ms per query
  Speedup:       25x

Dataset size: 100,000 vectors
  Without index: ~1000ms per query
  With index:    ~12ms per query
  Speedup:       83x

Conclusion: HNSW provides consistent sub-10ms performance
regardless of dataset size!
*/