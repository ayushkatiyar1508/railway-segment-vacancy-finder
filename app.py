import os
from datetime import date
from flask import Flask, render_template, request, jsonify
import requests

app = Flask(__name__)
API_BASE = "https://api.railradar.in/v1"
API_KEY = os.getenv("RAILRADAR_API_KEY", "").strip()
TIMEOUT = 12

def railradar(path, params=None):
    if not API_KEY:
        return None, {"error": "RAILRADAR_API_KEY is not configured on the server."}, 500
    try:
        r = requests.get(f"{API_BASE}{path}", headers={"Authorization": f"Bearer {API_KEY}", "Accept": "application/json"}, params=params, timeout=TIMEOUT)
    except requests.RequestException as exc:
        return None, {"error": f"RailRadar connection failed: {exc}"}, 502
    try:
        payload = r.json()
    except ValueError:
        payload = {"error": f"RailRadar returned HTTP {r.status_code}"}
    if not r.ok or payload.get("success") is False:
        err = payload.get("error")
        msg = err.get("message") if isinstance(err, dict) else err
        return r, {"error": msg or f"RailRadar returned HTTP {r.status_code}", "provider_status": r.status_code}, (502 if r.status_code >= 500 else r.status_code)
    return r, payload, 200

def data_of(payload):
    return payload.get("data", payload)

@app.get("/")
def index():
    return render_template("index.html")

@app.get("/api/stations")
def stations():
    q = request.args.get("q", "").strip()
    if len(q) < 2: return jsonify({"stations": []})
    _, p, s = railradar("/lookup/search/stations", {"q": q, "limit": 10})
    return jsonify({"stations": data_of(p), "data_mode": "RAILRADAR"}) if s == 200 else (jsonify(p), s)

@app.get("/api/train-search")
def train_search():
    q = request.args.get("q", "").strip()
    if len(q) < 2: return jsonify({"trains": []})
    _, p, s = railradar("/lookup/search/trains", {"q": q, "limit": 10})
    return jsonify({"trains": data_of(p), "data_mode": "RAILRADAR"}) if s == 200 else (jsonify(p), s)

@app.get("/api/trains")
def trains():
    source = request.args.get("source", "").strip().upper()
    destination = request.args.get("destination", "").strip().upper()
    if not source or not destination: return jsonify({"error": "Source and destination station codes are required."}), 400
    journey_date = request.args.get("date", "").strip()
    params = {"live": "true"}
    if journey_date:
        params["date"] = journey_date\n    _, p, s = railradar(f"/trains/between/{source}/{destination}", params)
    if s != 200: return jsonify(p), s
    d = data_of(p)
    return jsonify({"from": d.get("from"), "to": d.get("to"), "trains": d.get("trains", []), "data_mode": "RAILRADAR"})

@app.get("/api/train/<number>")
def train(number):
    _, p, s = railradar(f"/trains/{number}")
    return jsonify({"train": data_of(p), "data_mode": "RAILRADAR"}) if s == 200 else (jsonify(p), s)

@app.get("/api/status/<number>")
def status(number):
    _, p, s = railradar(f"/trains/{number}/live")
    return jsonify({"status": data_of(p), "data_mode": "RAILRADAR"}) if s == 200 else (jsonify(p), s)

@app.get("/api/availability")
def availability():
    number = request.args.get("train", "").strip()
    source = request.args.get("source", "").strip().upper()
    destination = request.args.get("destination", "").strip().upper()
    journey_date = request.args.get("journeyDate", "").strip() or date.today().isoformat()
    class_code = request.args.get("classCode", "3A").strip().upper()
    quota_code = request.args.get("quotaCode", "GN").strip().upper()
    if not number or not source or not destination: return jsonify({"error": "Train number, source, and destination are required."}), 400
    _, p, s = railradar(f"/trains/{number}/seats", {"journeyDate": journey_date, "source": source, "destination": destination, "classCode": class_code, "quotaCode": quota_code})
    if s in (401, 403):
        p["message"] = "Seat availability is not enabled for the current RailRadar Free/Sandbox plan. The API connection works, but this feature may require a paid plan."
    return jsonify({"availability": data_of(p), "data_mode": "RAILRADAR"}) if s == 200 else (jsonify(p), s)

@app.get("/api/vacancy")
def vacancy():
    return jsonify({"error": "Exact live berth-by-berth segment vacancy is not exposed by the current provider response. It returns availability status/counts, not the complete coach occupancy map. This app will not invent berth numbers.", "data_mode": "LIMITED_BY_PROVIDER"}), 501

@app.get("/api/health")
def health():
    return jsonify({"ok": bool(API_KEY), "provider": "RailRadar", "message": "API key configured" if API_KEY else "RAILRADAR_API_KEY is missing"})

@app.get("/api/config")
def config():
    return jsonify({"railradar_configured": bool(API_KEY), "provider": "RailRadar", "exact_segment_berth_data": False})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
