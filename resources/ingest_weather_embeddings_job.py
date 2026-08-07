#!/usr/bin/env python3
"""
Scheduled Weather Data Ingestion Job

This script runs as a Databricks Job to periodically sync weather data.
Scheduled to run every 6 hours to keep data fresh.
"""

import sys
import logging
from datetime import datetime
from collections import Counter

sys.path.append('/Workspace/Users/bhavikamange1993@gmail.com/weather-vector-retrieval-service')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_table_counts(conn):
    """Get current row counts from database tables."""
    with conn.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM weather_documents")
        doc_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM weather_embeddings")
        emb_count = cursor.fetchone()[0]
        
    return doc_count, emb_count


def main():
    """Main ingestion job logic."""
    start_time = datetime.now()
    logger.info("=" * 80)
    logger.info("Starting Weather Data Ingestion Job")
    logger.info(f"Start Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)
    
    try:
        from services.weather_service import WeatherService
        from lakebase import get_connection
        
        with get_connection() as conn:
            initial_docs, initial_embs = get_table_counts(conn)
            logger.info(f"Initial state: {initial_docs} documents, {initial_embs} embeddings")
            
            logger.info("Initializing Weather Service...")
            weather_service = WeatherService()
            
            logger.info("Fetching weather data...")
            documents = weather_service.fetch_and_store_weather_data()
            
            logger.info(f"Successfully fetched {len(documents)} weather documents")
            logger.info("Document types:")
            
            type_counts = Counter(doc.get('source_type', 'unknown') for doc in documents)
            for source_type, count in type_counts.items():
                logger.info(f"  - {source_type}: {count}")
            
            final_docs, final_embs = get_table_counts(conn)
            
            docs_added = final_docs - initial_docs
            embs_added = final_embs - initial_embs
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            logger.info("=" * 80)
            logger.info("Ingestion Job Complete")
            logger.info(f"End Time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"Duration: {duration:.2f} seconds")
            logger.info(f"Documents added: {docs_added}")
            logger.info(f"Embeddings added: {embs_added}")
            logger.info(f"Final state: {final_docs} documents, {final_embs} embeddings")
            logger.info("=" * 80)
        
        return 0
        
    except Exception as e:
        logger.error("=" * 80)
        logger.error("Ingestion Job Failed")
        logger.error(f"Error: {str(e)}")
        logger.error("=" * 80, exc_info=True)
        raise


if __name__ == "__main__":
    sys.exit(main())