# Weather Vector Retrieval Service - Quick Start

## 🚀 5-Minute Setup

Get your weather intelligence system running with scheduled data refresh in 5 minutes.

---

## Prerequisites

- Databricks workspace with Lakebase PostgreSQL enabled
- Databricks CLI installed and configured
- Python 3.8+ (for local testing)

---

## Step 1: Set Up Database (2 minutes)

Run the SQL setup scripts in order:

```sql
-- 1. Create documents table
sql/01_setup_weather_documents_table.sql

-- 2. Create embeddings table (includes HNSW index)
sql/02_setup_embeddings_table.sql
```

Verify:
```sql
SELECT COUNT(*) FROM weather_documents;
SELECT COUNT(*) FROM weather_embeddings;
```

---

## Step 2: Configure Secrets (1 minute)

Store your Lakebase connection URL in Databricks Secrets:

```bash
databricks secrets create-scope database
databricks secrets put-secret database support-lakebase-url
```

Format: `postgresql://user:password@host:port/database`

---

## Step 3: Deploy Scheduled Job (1 minute)

```bash
# From project root
databricks bundle deploy

# Verify deployment
databricks jobs list | grep "Weather Data Ingestion"
```

The job will now run automatically every 6 hours!

---

## Step 4: Initial Data Load (1 minute)

Don't wait 6 hours - trigger the first run now:

```bash
databricks jobs run-now --job-name "Weather Data Ingestion - Every 6 Hours"
```

Monitor progress in Databricks UI:
1. Go to **Workflows** → **Jobs**
2. Click "Weather Data Ingestion - Every 6 Hours"
3. Watch the logs in real-time

---

## Step 5: Test the Search API

### Option A: Use the Web UI

1. Deploy the Flask app:
   ```bash
   databricks apps deploy
   ```

2. Open the search interface:
   ```
   https://<your-workspace>.databricks.com/apps/<app-name>/weather/search
   ```

3. Try a query:
   ```
   "Will there be flooding near rivers?"
   ```

### Option B: Use the API Directly

```bash
curl -X POST https://<app-url>/weather/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "severe weather warnings",
    "source_types": ["alert"]
  }'
```

---

## ✅ You're Done!

Your weather intelligence system is now:
- ✅ Fetching weather data automatically every 6 hours
- ✅ Generating vector embeddings for semantic search
- ✅ Using HNSW index for 10-100x faster queries
- ✅ Serving a beautiful search UI
- ✅ Monitoring and alerting on job failures

---

## What Happens Next?

### Every 6 Hours:
1. Job fetches latest weather alerts, forecasts, and discussions
2. Normalizes and stores documents in PostgreSQL
3. Generates 384-dimensional embeddings
4. Updates HNSW vector index
5. Logs metrics (documents added, time taken, etc.)

### When You Search:
1. Your query is converted to a 384-d vector
2. HNSW index finds similar weather documents in <10ms
3. Results ranked by cosine similarity
4. UI displays with source badges and locations

---

## Common Next Steps

### Adjust Schedule

Edit `resources/ingest_weather_embeddings.job.yml`:

```yaml
schedule:
  quartz_cron_expression: "0 0 */3 * * ?"  # Every 3 hours
```

Redeploy:
```bash
databricks bundle deploy
```

### Add More Locations

The job currently uses a default forecast office. To add more:

1. Edit `weather_client.py`
2. Update `fetch_weather_documents()` to include your locations
3. Redeploy

### Benchmark Performance

Run the HNSW benchmark:
```bash
python notebooks/hnsw_index_benchmark.py
```

See typical results:
- Without index: 50-500ms per query
- With HNSW: 1-10ms per query
- Speedup: **10-100x** 🚀

### Monitor Job Health

```bash
# List recent runs
databricks jobs runs list \
  --job-name "Weather Data Ingestion - Every 6 Hours" \
  --limit 10

# Get run details
databricks jobs runs get --run-id <run_id>
```

---

## Troubleshooting

### Job Fails Immediately

**Check logs first:**
1. Databricks UI → Workflows → Jobs → Latest Run → Logs

**Common issues:**
- Missing Lakebase secret: Add `database/support-lakebase-url`
- Wrong database schema: Verify tables exist
- Library conflicts: Job uses single-node cluster with fresh libs

### No Data in Search Results

**Check if data was ingested:**
```sql
SELECT COUNT(*) FROM weather_documents;
SELECT COUNT(*) FROM weather_embeddings;
```

**If counts are 0:**
- Run the job manually: `databricks jobs run-now ...`
- Check job logs for errors

### Slow Search Queries

**Verify HNSW index exists:**
```sql
SELECT indexname 
FROM pg_indexes 
WHERE tablename = 'weather_embeddings';
```

**If missing, recreate:**
```sql
CREATE INDEX idx_weather_embeddings_embedding
ON weather_embeddings
USING hnsw (embedding vector_cosine_ops);
```

---

## Architecture Diagram

```
┌───────────────────────────────────────┐
│  Scheduled Job (Every 6 hours)     │
│                                       │
│  1. Fetch NWS API                   │
│  2. Store Documents                 │
│  3. Generate Embeddings             │
│  4. Update HNSW Index               │
└───────────────────┬───────────────────┘
                    │
                    v
         ┌──────────────────┐
         │  Lakebase        │
         │  PostgreSQL      │
         │                  │
         │  + pgvector      │
         │  + HNSW index    │
         └────────┬─────────┘
                  │
                  v
    ┌────────────────────────────────┐
    │      Flask Search API          │
    │                                │
    │  1. Convert query to vector  │
    │  2. HNSW similarity search   │
    │  3. Return top-k results     │
    └────────────┬───────────────────┘
                 │
                 v
      ┌──────────────────────┐
      │   Web UI / User      │
      │                      │
      │   Query: "flooding  │
      │   near rivers?"     │
      └──────────────────────┘
```

---

## Next Steps

✅ **Read the full documentation**: `README.md`  
✅ **Learn about HNSW performance**: `HNSW_BENCHMARK.md`  
✅ **Job configuration details**: `resources/README.md`  
✅ **Customize for your needs**: Edit source types, locations, schedule  

---

## Support

For issues or questions:
1. Check the logs in Databricks UI
2. Review the README files
3. Run the HNSW benchmark to verify performance

Happy weather searching! ⛅🌦️⚡