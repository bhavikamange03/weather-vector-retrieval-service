"""
Weather Intelligence Flask Application.

Endpoints:
    POST /weather/sync
"""


from flask import Flask, request, jsonify, render_template


from services.weather_service import (
    sync_weather
)

from services.weather_retriever import search_weather


app = Flask(__name__)



@app.route("/")
def home():

    return {
        "message":
        "Weather Intelligence API running"
    }

@app.route("/weather/test")
def weather_test():

    locations = [
        {
            "name": "Chicago, IL",
            "lat": 41.8781,
            "lon": -87.6298,
            "state": "IL"
        }
    ]

    result = sync_weather(
        locations,
        limit=20
    )

    return {
        "synced": result
    }

@app.route(
    "/weather/sync",
    methods=["POST"]
)
def weather_sync():


    data = request.get_json()


    if not data:

        return jsonify(
            {
                "error":
                "JSON body required"
            }
        ), 400



    locations = data.get(
        "locations",
        []
    )


    limit = data.get(
        "limit",
        50
    )


    if not locations:

        return jsonify(
            {
                "error":
                "locations list required"
            }
        ),400



    try:

        count = sync_weather(
            locations,
            limit
        )


        return jsonify(
            {
                "synced":
                count
            }
        )


    except Exception as e:


        return jsonify(
            {
                "error":
                str(e)
            }
        ),500


@app.route("/weather/search", methods=["GET"])
def weather_search_page():
    """Serve the weather search UI page."""
    return render_template("weather_search.html")


@app.route("/weather/search", methods=["POST"])
def weather_search():
    """API endpoint for weather search with optional source type filtering."""
    data = request.json

    query = data.get("query")
    source_types = data.get("source_types", None)  # Optional: ['alert', 'forecast', 'discussion']

    if not query:
        return jsonify({
            "error": "query parameter required"
        }), 400

    # Validate source_types if provided
    valid_types = ['alert', 'forecast', 'discussion']
    if source_types:
        if not isinstance(source_types, list):
            return jsonify({
                "error": "source_types must be a list"
            }), 400
        
        invalid = [t for t in source_types if t not in valid_types]
        if invalid:
            return jsonify({
                "error": f"Invalid source_types: {invalid}. Valid types: {valid_types}"
            }), 400

    results = search_weather(query, source_types=source_types)

    return {
        "query": query,
        "source_types": source_types or "all",
        "results": results
    }

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=8000
    )