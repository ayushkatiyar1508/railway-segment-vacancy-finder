import os
import re
from datetime import date
from flask import Flask, jsonify, render_template, request
import requests

app = Flask(__name__)
API_BASE = os.getenv("RAILRADAR_API_BASE", "https://api.railradar.in/v1").rstrip("/")
API_KEY = os.getenv("RAILRADAR_API_KEY", "").strip()
TIMEOUT = max(3, min(int(os.getenv("RAILRADAR_TIMEOUT", "12")), 30))
STATION_RE = re.compile(r"^[A-Z0-9]{2,8}$")
TRAIN_RE = re.compile(r"^[0-9]{1,6}$")
CLASS_CODES = {"1A", "2A", "3A", "3E", "CC", "EC", "SL", "2S", "EA"}
QUOTA_CODES = {"GN", "TQ", "LD", "SS", "HP", "PH", "DP", "PT"}

def provider_get(path, params=None):
    if not API_KEY:
        return {"error": "Railway data is not configured. Add RAILRADAR_API_KEY in the hosting environment."}, 503
    try:
        response = requests.get(
            f"{API_BASE}{path}",
            headers={"Authorization": f"Bearer {API_KEY}", "Accept": "application/json"},
            params=params or {},
            timeout=TIMEOUT,
        )
    except requests.Timeout:
        return {"error": "The railway data provider timed out. Please try again."}, 504
    except requests.RequestException:
        app.logger.exception("RailRadar request failed")
        return {"error": "Could not connect to the railway data provider. Please try again later."}, 502

    try:
        payload = response.json()
    except ValueError:
        payload = {}

    if not response.ok or (isinstance(payload, dict) and payload.get("success") is False):
        error = payload.get("error") if isinstance(payload, dict) else None
        message = error.get("message") if isinstance(error, dict) else error
        if response.status_code in (401, 403):
            message = "The provider rejected this request. Check the API key and plan permissions."
        elif not message:
            message = f"Railway data provider returned HTTP {response.status_code}."
        return {"error": str(message), "provider_status": response.status_code}, (
            response.status_code if response.status_code < 500 else 502
        )
    return payload, 200

def data_of(payload):
    if isinstance(payload, dict):
        return payload.get("data", payload)
    return payload

def as_list(value, key=None):
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        if key and isinstance(value.get(key), list):
            return value[key]
        for candidate in ("stations", "trains", "results", "items"):
            if isinstance(value.get(candidate), list):
                return value[candidate]
    return []

def valid_station(value):
    return bool(STATION_RE.fullmatch(value or ""))

def valid_train(value):
    return bool(TRAIN_RE.fullmatch(value or ""))

@app.get("/")
def index():
    return render_template("index.html")

@app.get("/api/health")
def health():
    configured = bool(API_KEY)
    return jsonify({
        "ok": configured,
        "provider": "RailRadar",
        "configured": configured,
        "message": "API key configured" if configured else "RAILRADAR_API_KEY is missing",
    }), (200 if configured else 503)

@app.get("/api/config")
def config():
    return jsonify({
        "railradar_configured": bool(API_KEY),
        "provider": "RailRadar",
        "exact_segment_berth_data": False,
    })

@app.get("/api/stations")
def stations():
    query = request.args.get("q", "").strip()
    if len(query) < 2:
        return jsonify({"stations": []})
    payload, status_code = provider_get("/lookup/search/stations", {"q": query, "limit": 10})
    if status_code != 200:
        return jsonify(payload), status_code
    return jsonify({"stations": as_list(data_of(payload), "stations"), "data_mode": "RAILRADAR"})

@app.get("/api/train-search")
def train_search():
    query = request.args.get("q", "").strip()
    if len(query) < 2:
        return jsonify({"trains": []})
    payload, status_code = provider_get("/lookup/search/trains", {"q": query, "limit": 10})
    if status_code != 200:
        return jsonify(payload), status_code
    return jsonify({"trains": as_list(data_of(payload), "trains"), "data_mode": "RAILRADAR"})

@app.get("/api/trains")
def trains():
    source = request.args.get("source", "").strip().upper()
    destination = request.args.get("destination", "").strip().upper()
    journey_date = request.args.get("date", "").strip()
    if not valid_station(source) or not valid_station(destination):
        return jsonify({"error": "Select valid source and destination station codes from the suggestions."}), 400
    if source == destination:
        return jsonify({"error": "Source and destination must be different stations."}), 400
    params = {"live": "true"}
    if journey_date:
        try:
            date.fromisoformat(journey_date)
        except ValueError:
            return jsonify({"error": "Date must be in YYYY-MM-DD format."}), 400
        params["date"] = journey_date
    payload, status_code = provider_get(f"/trains/between/{source}/{destination}", params)
    if status_code != 200:
        return jsonify(payload), status_code
    data = data_of(payload)
    if isinstance(data, list):
        train_list, origin, target = data, source, destination
    elif isinstance(data, dict):
        train_list = as_list(data, "trains")
        origin, target = data.get("from", source), data.get("to", destination)
    else:
        train_list, origin, target = [], source, destination
    return jsonify({"from": origin, "to": target, "trains": train_list, "data_mode": "RAILRADAR"})

@app.get("/api/train/<number>")
def train(number):
    if not valid_train(number):
        return jsonify({"error": "Train number must contain 1–6 digits."}), 400
    payload, status_code = provider_get(f"/trains/{number}")
    if status_code != 200:
        return jsonify(payload), status_code
    return jsonify({"train": data_of(payload), "data_mode": "RAILRADAR"})

@app.get("/api/status/<number>")
def status(number):
    if not valid_train(number):
        return jsonify({"error": "Train number must contain 1–6 digits."}), 400
    payload, status_code = provider_get(f"/trains/{number}/live")
    if status_code != 200:
        return jsonify(payload), status_code
    return jsonify({"status": data_of(payload), "data_mode": "RAILRADAR"})

@app.get("/api/availability")
def availability():
    number = request.args.get("train", "").strip()
    source = request.args.get("source", "").strip().upper()
    destination = request.args.get("destination", "").strip().upper()
    journey_date = request.args.get("journeyDate", "").strip() or date.today().isoformat()
    class_code = request.args.get("classCode", "3A").strip().upper()
    quota_code = request.args.get("quotaCode", "GN").strip().upper()

    if not valid_train(number):
        return jsonify({"error": "Enter a valid train number."}), 400
    if not valid_station(source) or not valid_station(destination) or source == destination:
        return jsonify({"error": "Enter valid, different source and destination station codes."}), 400
    try:
        date.fromisoformat(journey_date)
    except ValueError:
        return jsonify({"error": "Journey date must be in YYYY-MM-DD format."}), 400
    if class_code not in CLASS_CODES:
        return jsonify({"error": "Unsupported class code."}), 400
    if quota_code not in QUOTA_CODES:
        return jsonify({"error": "Unsupported quota code."}), 400

    payload, status_code = provider_get(
        f"/trains/{number}/seats",
        {
            "journeyDate": journey_date,
            "source": source,
            "destination": destination,
            "classCode": class_code,
            "quotaCode": quota_code,
        },
    )
    if status_code != 200:
        return jsonify(payload), status_code
    return jsonify({"availability": data_of(payload), "data_mode": "RAILRADAR"})

@app.get("/api/segment-availability")
def segment_availability():
    number = request.args.get("train", "").strip()
    raw_stations = request.args.get("stations", "").strip()
    journey_date = request.args.get("journeyDate", "").strip() or date.today().isoformat()
    class_code = request.args.get("classCode", "3A").strip().upper()
    quota_code = request.args.get("quotaCode", "GN").strip().upper()

    if not valid_train(number):
        return jsonify({"error": "Enter a valid train number."}), 400
    stations = [item.strip().upper() for item in raw_stations.split(",") if item.strip()]
    if len(stations) < 2:
        return jsonify({"error": "Enter at least two station codes, in travel order, separated by commas."}), 400
    if len(stations) > 12:
        return jsonify({"error": "Use at most 12 stations per route check."}), 400
    if any(not valid_station(code) for code in stations):
        return jsonify({"error": "Station codes must be 2–8 letters/numbers. Use official station codes."}), 400
    if len(set(stations)) != len(stations):
        return jsonify({"error": "A station appears more than once. Check the route order."}), 400
    try:
        date.fromisoformat(journey_date)
    except ValueError:
        return jsonify({"error": "Journey date must be in YYYY-MM-DD format."}), 400
    if class_code not in CLASS_CODES:
        return jsonify({"error": "Unsupported class code."}), 400
    if quota_code not in QUOTA_CODES:
        return jsonify({"error": "Unsupported quota code."}), 400

    legs = []
    for source, destination in zip(stations, stations[1:]):
        payload, status_code = provider_get(
            f"/trains/{number}/seats",
            {
                "journeyDate": journey_date,
                "source": source,
                "destination": destination,
                "classCode": class_code,
                "quotaCode": quota_code,
            },
        )
        if status_code != 200:
            legs.append({
                "from": source, "to": destination, "checked": False,
                "error": payload.get("error", "Availability could not be checked."),
                "provider_status": payload.get("provider_status"),
            })
            continue
        availability_data = data_of(payload)
        legs.append({
            "from": source, "to": destination, "checked": True,
            "availability": availability_data,
        })

    return jsonify({
        "train": number,
        "journeyDate": journey_date,
        "classCode": class_code,
        "quotaCode": quota_code,
        "legs": legs,
        "note": "Each leg shows the provider's reported ticket availability, not physical berth occupancy. Availability can change; book a valid ticket for each leg.",
        "data_mode": "RAILRADAR",
    })


@app.get("/api/vacancy")
def vacancy():
    return jsonify({
        "error": "The connected provider does not expose verified berth-by-berth occupancy for each route segment. This app will not guess berth numbers.",
        "data_mode": "LIMITED_BY_PROVIDER",
        "exact_segment_berth_data": False,
    }), 501

@app.errorhandler(404)
def not_found(_error):
    if request.path.startswith("/api/"):
        return jsonify({"error": "API endpoint not found."}), 404
    return "Page not found", 404

@app.errorhandler(500)
def server_error(_error):
    app.logger.exception("Unhandled server error")
    if request.path.startswith("/api/"):
        return jsonify({"error": "Unexpected server error. Check the server logs."}), 500
    return "Unexpected server error", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
