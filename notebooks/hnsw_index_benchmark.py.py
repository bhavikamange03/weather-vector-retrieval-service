# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "5"
# ///
# DBTITLE 1,HNSW Index Performance Benchmark
# MAGIC %md
# MAGIC # HNSW Index Performance Benchmark
# MAGIC
# MAGIC This notebook benchmarks the performance improvement of using an **HNSW (Hierarchical Navigable Small World)** index for vector similarity search on weather embeddings.
# MAGIC
# MAGIC ## What is HNSW?
# MAGIC
# MAGIC HNSW is a graph-based algorithm for approximate nearest neighbor search that provides:
# MAGIC - **Fast query performance** - Orders of magnitude faster than exact search
# MAGIC - **High recall** - Near-perfect accuracy despite being approximate
# MAGIC - **Scalability** - Works well with millions of vectors
# MAGIC
# MAGIC ## Benchmark Process
# MAGIC
# MAGIC 1. **Drop existing index** - Start with no index for baseline
# MAGIC 2. **Benchmark without index** - Measure query latency using exact vector search
# MAGIC 3. **Create HNSW index** - Build the index on the embedding column
# MAGIC 4. **Benchmark with index** - Measure query latency using HNSW
# MAGIC 5. **Compare results** - Calculate speedup and visualize improvements
# MAGIC
# MAGIC ## Expected Results
# MAGIC
# MAGIC HNSW indexes typically provide:
# MAGIC - **10-100x speedup** for vector similarity queries
# MAGIC - **Sub-millisecond response times** for most queries
# MAGIC - **Linear scalability** as data grows
# MAGIC
# MAGIC Let's see how our weather embeddings perform! 🚀

# COMMAND ----------

# DBTITLE 1,Install Dependencies
# MAGIC %pip uninstall -y psycopg2-binary
# MAGIC %pip install -q sqlalchemy sentence-transformers pandas matplotlib

# COMMAND ----------

# DBTITLE 1,Imports and Setup
import sys
sys.path.append('/Workspace/Users/bhavikamange1993@gmail.com/weather-vector-retrieval-service')

import time
import pandas as pd
import matplotlib.pyplot as plt
from sentence_transformers import SentenceTransformer
from lakebase import get_connection

print("✅ Imports successful")

# COMMAND ----------

# DBTITLE 1,Benchmark Configuration
# Load embedding model
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

# Test queries to benchmark
TEST_QUERIES = [
    "Will there be flooding near rivers?",
    "What is the temperature forecast?",
    "Are there any severe weather warnings?",
    "When will it rain?",
    "Is there a storm approaching?"
]

# Number of iterations per query
ITERATIONS = 10

print(f"✅ Benchmark configured with {len(TEST_QUERIES)} queries, {ITERATIONS} iterations each")

# COMMAND ----------

# DBTITLE 1,Benchmark Function
def run_vector_query(query_vector, limit=5):
    """
    Execute a vector similarity search query.
    Returns execution time in milliseconds.
    """
    sql = """
    SELECT
        document_id,
        chunk_index,
        chunk_text,
        1 - (embedding <=> %s::vector) AS similarity
    FROM weather_embeddings
    ORDER BY embedding <=> %s::vector
    LIMIT %s
    """
    
    start_time = time.time()
    
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, (query_vector, query_vector, limit))
            rows = cursor.fetchall()
    
    end_time = time.time()
    latency_ms = (end_time - start_time) * 1000
    
    return latency_ms, len(rows)


def benchmark_queries(test_queries, iterations=10):
    """
    Run benchmark on a set of queries.
    Returns DataFrame with results.
    """
    results = []
    
    for query_text in test_queries:
        # Generate embedding for query
        query_embedding = model.encode(query_text)
        query_vector = "[" + ",".join(map(str, query_embedding.tolist())) + "]"
        
        query_latencies = []
        
        for i in range(iterations):
            latency_ms, result_count = run_vector_query(query_vector)
            query_latencies.append(latency_ms)
        
        avg_latency = sum(query_latencies) / len(query_latencies)
        min_latency = min(query_latencies)
        max_latency = max(query_latencies)
        
        results.append({
            'query': query_text[:50] + '...' if len(query_text) > 50 else query_text,
            'avg_ms': avg_latency,
            'min_ms': min_latency,
            'max_ms': max_latency,
            'result_count': result_count
        })
    
    return pd.DataFrame(results)

print("✅ Benchmark functions defined")

# COMMAND ----------

# DBTITLE 1,Benchmark WITHOUT HNSW Index
# Drop the HNSW index if it exists
print("🗑️ Dropping HNSW index...")
with get_connection() as conn:
    with conn.cursor() as cursor:
        cursor.execute("DROP INDEX IF EXISTS idx_weather_embeddings_embedding;")
        conn.commit()

print("✅ Index dropped\n")

# Run benchmark WITHOUT index
print("🔥 Running benchmark WITHOUT HNSW index...")
results_without_index = benchmark_queries(TEST_QUERIES, ITERATIONS)

print("\n" + "="*80)
print("RESULTS WITHOUT HNSW INDEX")
print("="*80)
print(results_without_index.to_string(index=False))
print(f"\nAverage query latency: {results_without_index['avg_ms'].mean():.2f} ms")
print("="*80)

# COMMAND ----------

# DBTITLE 1,Create HNSW Index
# Create HNSW index
print("🔨 Creating HNSW index...")
start = time.time()

with get_connection() as conn:
    with conn.cursor() as cursor:
        cursor.execute("""
            CREATE INDEX idx_weather_embeddings_embedding
            ON weather_embeddings
            USING hnsw (embedding vector_cosine_ops)
        """)
        conn.commit()

index_creation_time = time.time() - start
print(f"✅ HNSW index created in {index_creation_time:.2f} seconds")

# Let the index settle
time.sleep(2)

# COMMAND ----------

# DBTITLE 1,Benchmark WITH HNSW Index
# Run benchmark WITH index
print("🚀 Running benchmark WITH HNSW index...")
results_with_index = benchmark_queries(TEST_QUERIES, ITERATIONS)

print("\n" + "="*80)
print("RESULTS WITH HNSW INDEX")
print("="*80)
print(results_with_index.to_string(index=False))
print(f"\nAverage query latency: {results_with_index['avg_ms'].mean():.2f} ms")
print("="*80)

# COMMAND ----------

# DBTITLE 1,Compare Results and Visualize
# Compare results
comparison = pd.DataFrame({
    'Query': results_without_index['query'],
    'Without Index (ms)': results_without_index['avg_ms'],
    'With Index (ms)': results_with_index['avg_ms'],
    'Speedup': results_without_index['avg_ms'] / results_with_index['avg_ms']
})

print("\n" + "="*100)
print("PERFORMANCE COMPARISON")
print("="*100)
print(comparison.to_string(index=False))

avg_without = results_without_index['avg_ms'].mean()
avg_with = results_with_index['avg_ms'].mean()
speedup = avg_without / avg_with

print("\n" + "="*100)
print("SUMMARY")
print("="*100)
print(f"Average latency WITHOUT index: {avg_without:.2f} ms")
print(f"Average latency WITH index:    {avg_with:.2f} ms")
print(f"Average speedup:                {speedup:.2f}x faster")
print(f"Latency reduction:              {((avg_without - avg_with) / avg_without * 100):.1f}%")
print("="*100)

# Visualization
fig, axes = plt.subplots(1, 2, figsize=(16, 6))

# Bar chart comparing latencies
ax1 = axes[0]
queries_short = [q[:20] + '...' for q in results_without_index['query']]
x = range(len(queries_short))
width = 0.35

ax1.bar([i - width/2 for i in x], results_without_index['avg_ms'], width, 
        label='Without HNSW Index', color='#ff5252', alpha=0.8)
ax1.bar([i + width/2 for i in x], results_with_index['avg_ms'], width,
        label='With HNSW Index', color='#4caf50', alpha=0.8)

ax1.set_xlabel('Query', fontsize=12, fontweight='bold')
ax1.set_ylabel('Average Latency (ms)', fontsize=12, fontweight='bold')
ax1.set_title('Query Latency Comparison', fontsize=14, fontweight='bold')
ax1.set_xticks(x)
ax1.set_xticklabels(queries_short, rotation=45, ha='right')
ax1.legend()
ax1.grid(axis='y', alpha=0.3)

# Speedup chart
ax2 = axes[1]
speedups = comparison['Speedup'].values
colors = ['#4caf50' if s > 1 else '#ff5252' for s in speedups]

ax2.barh(queries_short, speedups, color=colors, alpha=0.8)
ax2.axvline(x=1, color='black', linestyle='--', linewidth=1, label='No improvement')
ax2.set_xlabel('Speedup Factor (x)', fontsize=12, fontweight='bold')
ax2.set_ylabel('Query', fontsize=12, fontweight='bold')
ax2.set_title('HNSW Index Speedup', fontsize=14, fontweight='bold')
ax2.legend()
ax2.grid(axis='x', alpha=0.3)

plt.tight_layout()
plt.show()

print("\n✅ Benchmark complete!")