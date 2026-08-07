# Weather Intelligence — Lakebase Vector Search

> 📘 **Technical Design Document**: For detailed explanations of data source selection, schema decisions, chunking strategy, and known limitations, see **[README_WEATHER.md](README_WEATHER.md)**

## Overview

Weather Intelligence is an end-to-end Retrieval-Augmented Generation (RAG) style pipeline that ingests unstructured weather data, stores it in Databricks Lakebase PostgreSQL, generates vector embeddings using Sentence Transformers, and enables semantic search using PostgreSQL pgvector.

The application pipeline:

1. Harvest weather alerts and forecast narratives from the National Weather Service (NWS) API.
2. Store normalized weather documents in Lakebase.
3. Chunk and generate embeddings for weather text.
4. Perform semantic search using vector similarity.

---

# Architecture

```
                     User
                       |
                       |
                Flask REST API
                       |
        --------------------------------
        |                              |
        |                              |
   /weather/sync                /weather/search
        |                              |
        |                              |
        v                              v
 weather_service.py          Vector Retrieval Service
        |
        |
 weather_client.py
        |
        |
 National Weather Service API
        |
        |
        v
 weather_documents
        |
        |
        v
 Embedding Pipeline
        |
        |
        v
 weather_chunk_embeddings
        |
        |
        v
       pgvector
```

---

# Technology Stack

- Python
- Flask
- Databricks Apps
- Databricks Lakebase (PostgreSQL)
- PostgreSQL pgvector
- psycopg2
- sentence-transformers
- National Weather Service API

---

# Data Source

## National Weather Service API

Source:

```
https://api.weather.gov
```

The National Weather Service API was selected because:

- It is free.
- No API key is required.
- It provides high-quality unstructured text.
- Weather alerts contain detailed descriptions and safety instructions.
- Forecast endpoints provide natural language weather information.

---

## APIs Used

### Active Weather Alerts

Endpoint:

```
GET /alerts/active?area={state}
```

Used fields:

- event
- description
- instruction
- effective time


Example:

```
Flood Warning

Heavy rainfall may cause flooding near rivers and low-lying areas.
```

---

### Forecast Data

First resolve location:

```
GET /points/{latitude},{longitude}
```

Then retrieve forecast:

```
GET /gridpoints/{office}/{x},{y}/forecast
```

Used field:

```
detailedForecast
```

Example:

```
Sunny, with a high near 78.
Northwest wind around 6 mph.
```

---

# Project Structure

```
weather-intelligence/

│
├── app.py
├── lakebase.py
├── weather_client.py
│
├── services/
│   ├── weather_service.py
│   └── weather_retriever.py
│
├── notebooks/
│   ├── ingest_weather_embeddings.py
│   ├── test_retriever.py
│   └── hnsw_index_benchmark.py
│
├── resources/
│   ├── ingest_weather_embeddings_job.py
│   ├── ingest_weather_embeddings.job.yml
│   └── README.md
│
├── sql/
│   ├── 01_setup_weather_documents_table.sql
│   ├── 02_setup_weather_embeddings_table.sql
│   ├── 03_setup_weather_chunk_embeddings_table.sql
│   └── 04_hnsw_index_benchmark.sql
│
├── templates/
│   └── weather_search.html
│
├── README.md
├── README_WEATHER.md                        # Technical design document
├── QUICKSTART.md                            # 5-minute setup guide
├── HNSW_BENCHMARK.md                        # Vector index performance
├── requirements.txt
├── app.yaml
└── databricks.yml
```

---

# Database Design

## weather_documents

Stores normalized weather information.

```sql
CREATE TABLE weather_documents (

    id TEXT PRIMARY KEY,

    location TEXT,

    source_type TEXT,

    headline TEXT,

    narrative_text TEXT,

    issued_at TIMESTAMP,

    payload JSONB,

    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

Purpose:

- Stores original weather text.
- Maintains source metadata.
- Preserves raw API payload for traceability.

---

## weather_embeddings

Stores document-level embeddings.

```sql
CREATE TABLE weather_embeddings (

    id SERIAL PRIMARY KEY,

    document_id TEXT,

    embedding VECTOR(384),

    model_name TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## weather_chunk_embeddings

Stores chunk-level embeddings used for semantic retrieval.

```sql
CREATE TABLE weather_chunk_embeddings (

    id SERIAL PRIMARY KEY,

    document_id TEXT,

    chunk_index INTEGER,

    chunk_text TEXT,

    embedding VECTOR(384),

    model_name TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

# Embedding Model

Model used:

```
sentence-transformers/all-MiniLM-L6-v2
```

Details:

- Embedding dimension: 384
- Lightweight transformer model
- Optimized for semantic similarity search

The same model is used for:

- Document embeddings
- Query embeddings

This ensures compatibility during vector retrieval.

---

# Chunking Strategy

Weather descriptions are usually short, but long alert messages may contain multiple concepts.

Chunking configuration:

```
CHUNK_SIZE = 800 characters

CHUNK_OVERLAP = 100 characters
```

A sliding window approach is used.

Example:

```
Original Document

[----------------800----------------]


Chunk 1

[----------------]


Chunk 2

        [----------------]
```

The overlap preserves context between chunks.

---

# Automated Data Refresh

## Scheduled Ingestion Job

The application includes a Databricks Job that automatically syncs weather data every 6 hours, ensuring your search results are always current.

### Features:

- **Automatic Scheduling**: Runs at 00:00, 06:00, 12:00, and 18:00 daily
- **Multi-Source Ingestion**: Fetches alerts, forecasts, and forecast discussions
- **Automatic Embedding**: Generates vector embeddings for all new content
- **Error Handling**: Built-in retry logic and email notifications on failure
- **Monitoring**: Detailed logs showing documents added, processing time, and metrics

### Quick Start:

```bash
# Deploy the scheduled job
databricks bundle deploy --target <your_target>

# Verify it's running
databricks jobs list --output JSON | grep "Weather Data Ingestion"

# Manually trigger a run
databricks jobs run-now --job-name "Weather Data Ingestion - Every 6 Hours"
```

### Configuration:

The job is defined in `resources/ingest_weather_embeddings.job.yml`.

To adjust the schedule (e.g., every 3 hours instead of 6):

```yaml
schedule:
  quartz_cron_expression: "0 0 */3 * * ?"  # Every 3 hours
```

### Monitoring:

- **Logs**: View in Databricks UI under Workflows → Jobs
- **Metrics**: Each run reports documents added, embeddings generated, and duration
- **Alerts**: Email notifications sent on job failure

For detailed documentation, see `resources/README.md`.

---

# API Endpoints

## 1. Sync Weather Data

### POST

```
/weather/sync
```

Request:

```json
{
  "locations": [
    {
      "name": "Chicago, IL",
      "lat": 41.8781,
      "lon": -87.6298,
      "state": "IL"
    }
  ],
  "limit": 50
}
```

Process:

1. Resolve weather grid information.
2. Fetch active alerts and forecasts.
3. Normalize weather responses.
4. Store documents in Lakebase.

Response:

```json
{
    "synced": 20
}
```

---

## 2. Semantic Weather Search

### POST

```
/weather/search
```

Request:

```json
{
    "query": "flash flood risk this weekend",
    "top_k": 5
}
```

Process:

1. Convert query text into embedding.
2. Search pgvector using cosine similarity.
3. Return most relevant weather documents.

Response:

```json
[
    {
        "location": "Chicago, IL",
        "headline": "Flood Warning",
        "chunk_text": "Heavy rainfall expected...",
        "similarity": 0.91
    }
]
```

---

# Running the Application

## 1. Create Lakebase Tables

Run SQL files:

```
sql/
 ├── 01_setup_weather_documents_table.sql
 ├── 02_setup_weather_embeddings_table.sql
 └── 03_setup_weather_chunk_embeddings_table.sql
```

Verify:

```sql
SELECT *
FROM weather_documents;
```

---

## 2. Configure Lakebase Connection

The application reads Lakebase credentials from Databricks Secrets.

Secret configuration:

```
Scope:
database

Key:
support-lakebase-url
```

---

## 3. Deploy Databricks App

Deploy the Flask application.

The app exposes:

```
/weather/sync
/weather/search
```

---

## 4. Run Weather Sync

Example:

```bash
POST /weather/sync
```

Verify:

```sql
SELECT COUNT(*)
FROM weather_documents;
```

---

## 5. Generate Embeddings

Run:

```bash
python notebooks/ingest_weather_embeddings.py
```

The pipeline:

```
weather_documents

        |

        v

Text Chunking

        |

        v

Sentence Transformer

        |

        v

pgvector embeddings

        |

        v

weather_chunk_embeddings
```

---

## 6. Search Weather Information

Example:

```json
{
 "query":"risk of flooding near rivers",
 "top_k":5
}
```

The API returns the most semantically similar weather documents.

---

# Current Limitations

- Location coordinates are currently provided by the API caller.
- Only National Weather Service data is used.

---

# Future Improvements

Possible enhancements:

- Add city name geocoding.
- Support multiple weather data providers.
- Add retrieval performance benchmarking.

---

# Author

Built as part of the Databricks Lakebase AI Application coursework.