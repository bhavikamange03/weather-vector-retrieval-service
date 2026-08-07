from lakebase import run_write
from psycopg2.extras import Json

from weather_client import (
    fetch_weather_documents
)



def sync_weather(locations, limit=50):

    synced = 0


    for location in locations:


        documents = fetch_weather_documents(

            location["name"],

            location["lat"],

            location["lon"],

            location["state"]

        )
        

        for doc in documents[:limit]:
            print(doc)
            print(type(doc))



            for key, value in doc.items():
                print(key, type(value))

            sql = """

            INSERT INTO weather_documents
            (
                id,
                location,
                source_type,
                headline,
                narrative_text,
                issued_at,
                payload
            )

            VALUES
            (
                %s,%s,%s,%s,%s,%s,%s
            )


            ON CONFLICT(id)

            DO UPDATE SET

            narrative_text =
                EXCLUDED.narrative_text,

            payload =
                EXCLUDED.payload,

            synced_at =
                CURRENT_TIMESTAMP

            """


            run_write(
                sql,
                (
                    doc["id"],
                    doc["location"],
                    doc["source_type"],
                    doc["headline"],
                    doc["narrative_text"],
                    doc["issued_at"],
                    Json(doc["payload"])
                )
            )


            synced += 1


    return synced