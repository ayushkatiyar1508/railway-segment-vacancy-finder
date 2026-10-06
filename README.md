# Railway Segment Vacancy Finder — Prototype

A Flask prototype for route search and segment-wise berth vacancy.

## Run locally
```bash
python -m venv .venv
# Windows:
.venv\\Scripts\\activate
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000

## Current status
This repository intentionally uses DEMO railway data. It does not scrape IRCTC, NTES, or passenger records.

The production version needs a permitted/authorized data provider for train search, schedules, seat availability, running status, and—if legally exposed—berth-level occupancy.

## Render
Build: `pip install -r requirements.txt`
Start: `gunicorn app:app`
