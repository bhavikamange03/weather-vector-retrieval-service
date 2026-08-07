# HNSW Index Performance Benchmark

## Overview

This benchmark measures the performance improvement of using an **HNSW (Hierarchical Navigable Small World)** index for vector similarity search on weather embeddings stored in Lakebase PostgreSQL.

## What is HNSW?

HNSW is a state-of-the-art graph-based algorithm for approximate nearest neighbor search that provides:

- **🚀 Fast Queries**: 10-100x faster than exact vector search
- **🎯 High Accuracy**: Near-perfect recall (>99%) despite being approximate
- **📈 Scalability**: Performance scales sub-linearly with dataset size
- **💾 Memory Efficient**: Reasonable memory overhead for the speed gains

## How HNSW Works

1. **Graph Structure**: Builds a multi-layer proximity graph
2. **Hierarchical Search**: Starts at top layer, drills down to find nearest neighbors
3. **Approximate Results**: Trades perfect accuracy for massive speed improvements
4. **pgvector Integration**: Native PostgreSQL extension for vector operations

## Running the Benchmark

### Option 1: Run the Python Notebook (Recommended)

1. Open the notebook:
   ```
   notebooks/hnsw_index_benchmark.py
   ```

2. Run all cells in order:
   - Cell 1: Install dependencies
   - Cell 2-3: Setup and configuration
   - Cell 4: Define benchmark functions
   - Cell 5: Benchmark WITHOUT index (baseline)
   - Cell 6: Create HNSW index
   - Cell 7: Benchmark WITH index
   - Cell 8: Compare results and visualize

3. Results include:
   - Detailed latency metrics per query
   - Average speedup across all queries
   - Visual charts comparing performance
   - Speedup factors per query type

### Option 2: Manual SQL Testing

Refer to `sql/04_hnsw_index_benchmark.sql` for:
- SQL syntax reference
- Parameter tuning guide
- Query plan analysis examples

## Expected Results

### Performance Improvements

| Dataset Size | Without Index | With HNSW Index | Speedup |
|--------------|---------------|-----------------|----------|
| 1,000 vectors | ~50ms | ~5ms | **10x** |
| 10,000 vectors | ~200ms | ~8ms | **25x** |
| 100,000 vectors | ~1000ms | ~12ms | **83x** |

### Key Metrics

- **Query Latency**: Reduced from 50-500ms to 1-10ms
- **Throughput**: Increased by 10-100x
- **Consistency**: Sub-10ms performance regardless of dataset size

## Index Configuration

### Default Settings (Recommended)

```sql
CREATE INDEX idx_weather_embeddings_embedding
ON weather_embeddings
USING hnsw (embedding vector_cosine_ops);
```

### Advanced Tuning

#### Build-time Parameters

```sql
CREATE INDEX idx_weather_embeddings_embedding
ON weather_embeddings
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

- **m**: Number of connections per layer
  - Default: 16
  - Range: 4-64
  - Higher = better recall, slower build

- **ef_construction**: Candidate list size during build
  - Default: 64
  - Range: 16-512
  - Higher = better recall, slower build

#### Query-time Parameter

```sql
SET hnsw.ef_search = 100;
```

- **ef_search**: Candidate list size during search
  - Default: 40
  - Range: 10-1000
  - Higher = better recall, slower queries

## Trade-offs

### Advantages ✅

- Dramatic query speed improvements (10-100x)
- Sub-linear scaling with dataset size
- High recall rates (>99%)
- Production-ready and battle-tested

### Considerations ⚠️

- Slightly slower writes (index must be updated)
- Additional storage space (~20-30% of table size)
- Approximate results (not exact, but >99% accurate)
- Index build time for large datasets

## Use Cases

HNSW is ideal for:

- ✅ **Semantic Search**: Finding similar documents
- ✅ **Recommendation Systems**: Content similarity
- ✅ **RAG Applications**: Relevant context retrieval
- ✅ **Image Search**: Visual similarity
- ✅ **Anomaly Detection**: Outlier identification

Not recommended for:

- ❌ Exact match requirements (use exact search)
- ❌ Very small datasets (<1000 vectors, overhead not worth it)
- ❌ Frequently changing embeddings (rebuilds expensive)

## Monitoring

### Check Index Size

```sql
SELECT
    pg_size_pretty(pg_relation_size('idx_weather_embeddings_embedding')) AS index_size,
    pg_size_pretty(pg_relation_size('weather_embeddings')) AS table_size;
```

### Check Index Usage

```sql
SELECT
    indexrelname,
    idx_scan AS scans,
    idx_tup_read AS tuples_read
FROM pg_stat_user_indexes
WHERE indexrelname = 'idx_weather_embeddings_embedding';
```

### Query Plan Analysis

```sql
EXPLAIN ANALYZE
SELECT ...
FROM weather_embeddings
ORDER BY embedding <=> '[...]'::vector
LIMIT 5;
```

Look for: `Index Scan using idx_weather_embeddings_embedding`

## Troubleshooting

### Slow Index Build

- Reduce `ef_construction` parameter
- Build during off-peak hours
- Consider building index on smaller sample first

### Lower Than Expected Speedup

- Ensure index is being used (check EXPLAIN ANALYZE)
- Increase `ef_search` for better recall
- Check if dataset is too small to benefit

### High Memory Usage

- Reduce `m` parameter
- Use lower `ef_construction` value
- Monitor with `pg_stat_user_indexes`

## References

- [pgvector Documentation](https://github.com/pgvector/pgvector)
- [HNSW Paper](https://arxiv.org/abs/1603.09320)
- [PostgreSQL Indexing Best Practices](https://www.postgresql.org/docs/current/indexes.html)

## Next Steps

1. ✅ Run the benchmark notebook
2. ✅ Analyze your specific performance gains
3. ✅ Tune parameters if needed
4. ✅ Monitor in production
5. ✅ Scale with confidence!

---

**Note**: The HNSW index is already created in `sql/02_setup_embeddings_table.sql`. This benchmark helps you understand and validate its performance impact.