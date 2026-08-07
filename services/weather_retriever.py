from sentence_transformers import SentenceTransformer

from lakebase import get_connection


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


model = SentenceTransformer(MODEL_NAME)



def search_weather(query, limit=5, source_types=None):
    """
    Search weather documents using vector similarity.
    
    Args:
        query: User's search query
        limit: Maximum number of results to return
        source_types: Optional list of source types to filter by ['alert', 'forecast', 'discussion']
                     If None, searches all types
    
    Returns:
        List of matching weather documents with similarity scores
    """

    # 1. Convert user question into embedding

    query_embedding = model.encode(query)


    # 2. Convert numpy array to pgvector format

    query_vector = (
        "["
        +
        ",".join(
            map(
                str,
                query_embedding.tolist()
            )
        )
        +
        "]"
    )


    # 3. Build SQL with optional source_type filter

    sql_base = """
    SELECT
        we.document_id,
        we.chunk_index,
        we.chunk_text,
        wd.source_type,
        wd.headline,
        wd.location,
        1 - (we.embedding <=> %s::vector) AS similarity
    FROM weather_embeddings we
    JOIN weather_documents wd ON we.document_id = wd.id
    """

    sql_filter = ""
    params = [query_vector, query_vector]

    if source_types and len(source_types) > 0:
        placeholders = ",".join(["%s"] * len(source_types))
        sql_filter = f" WHERE wd.source_type IN ({placeholders})"
        params.extend(source_types)

    sql_order = """
    ORDER BY we.embedding <=> %s::vector
    LIMIT %s
    """

    params.append(limit)

    sql = sql_base + sql_filter + sql_order


    # 4. Query Lakebase

    with get_connection() as conn:

        with conn.cursor() as cursor:

            cursor.execute(
                sql,
                tuple(params)
            )

            rows = cursor.fetchall()


    # 5. Convert database rows to API friendly format

    results = []

    for row in rows:

        results.append(
            {
                "document_id": row["document_id"],
                "chunk_index": row["chunk_index"],
                "text": row["chunk_text"],
                "source_type": row["source_type"],
                "headline": row["headline"],
                "location": row["location"],
                "similarity": float(row["similarity"])
            }
        )


    return results