import os
from flask import Flask, render_template, request, jsonify
import requests

app = Flask(__name__)

OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/weather")
def get_weather():
    city = request.args.get("city", "").strip()
    if not city:
        return jsonify({"error": "City name is required."}), 400

    if not OPENWEATHER_API_KEY:
        return jsonify({"error": "Server is missing OPENWEATHER_API_KEY."}), 500

    endpoint = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": city,
        "appid": OPENWEATHER_API_KEY,
        "units": "metric",
    }

    try:
        response = requests.get(endpoint, params=params, timeout=10)
        response.raise_for_status()
    except requests.exceptions.HTTPError:
        if response.status_code == 404:
            return jsonify({"error": "City not found. Check the name and try again."}), 404
        return jsonify({"error": "Weather service returned an error."}), response.status_code
    except requests.exceptions.RequestException:
        return jsonify({"error": "Unable to reach the weather service."}), 502

    payload = response.json()
    weather = payload.get("weather", [{}])[0]
    main = payload.get("main", {})

    result = {
        "city": payload.get("name", city),
        "country": payload.get("sys", {}).get("country", ""),
        "description": weather.get("description", "Unknown").title(),
        "temperature": main.get("temp"),
        "feels_like": main.get("feels_like"),
        "humidity": main.get("humidity"),
        "icon": weather.get("icon"),
        "icon_url": f"https://openweathermap.org/img/wn/{weather.get('icon')}@2x.png" if weather.get("icon") else None,
    }

    return jsonify(result)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
