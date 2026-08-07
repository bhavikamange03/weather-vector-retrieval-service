"""
Weather Intelligence Flask Application.

Endpoints:
    POST /weather/sync
"""


from flask import Flask, request, jsonify


from services.weather_service import (
    sync_weather
)



app = Flask(__name__)



@app.route("/")
def home():

    return {
        "message":
        "Weather Intelligence API running"
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




if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=8000
    )