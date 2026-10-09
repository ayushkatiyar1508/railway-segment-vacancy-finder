# Railway Finder — Route & Seat Availability

A responsive Flask application for Indian railway route search, station autocomplete, train lookup, running status, and seat-availability queries through the RailRadar API.

## Features

- Station autocomplete with station-code selection
- Train search by name or number
- Train search between two stations for a travel date
- Live running-status lookup
- Seat-availability lookup by train, journey segment, date, class, and quota
- JSON API health/config endpoints
- Input validation, timeouts, readable provider errors, and backend unit tests
- Responsive mobile-friendly interface

## Important data limitations

This app only displays data returned by the configured provider. It does **not** scrape IRCTC/NTES, bypass provider permissions, or invent seat/berth information.

The segment-wise berth finder is not implemented as live berth occupancy because the current integration has not established access to verified berth-by-berth occupancy for each route segment. Seat availability counts/statuses are not the same as a coach-wise berth map. Availability, live status, quotas, and rate limits depend on the API provider and subscription plan.

## Run locally

Python 3.10+ is recommended.

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

Set your API key in the environment (never commit API keys to GitHub):

**Windows PowerShell**
```powershell
$env:RAILRADAR_API_KEY="your_provider_api_key"
python app.py
```

**macOS/Linux**
```bash
export RAILRADAR_API_KEY="your_provider_api_key"
python app.py
```

Open http://127.0.0.1:5000.

Optional environment variables:
- `RAILRADAR_API_BASE`: defaults to `https://api.railradar.in/v1`
- `RAILRADAR_TIMEOUT`: request timeout in seconds (clamped to 3–30)

## Run tests

```bash
python -m unittest discover -s tests -v
```

Tests mock the external provider; they validate application behavior but do not prove that a real provider key, endpoint, or subscription plan works.

## Deploy on Render

- Runtime: Python
- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app`
- Add `RAILRADAR_API_KEY` under **Environment** in the Render service settings.
- Keep the key private; do not add it to source code or frontend JavaScript.
- After deployment, check `/api/health`. A configured key only confirms that the environment variable exists; it does not guarantee provider authentication or plan access.

## API routes

| Route | Purpose |
|---|---|
| `GET /` | Web interface |
| `GET /api/health` | API-key configuration health |
| `GET /api/config` | Provider capabilities/config flags |
| `GET /api/stations?q=Delhi` | Station search |
| `GET /api/train-search?q=Vande%20Bharat` | Train search |
| `GET /api/trains?source=NDLS&destination=CNB&date=YYYY-MM-DD` | Route train search |
| `GET /api/train/12345` | Train details |
| `GET /api/status/12345` | Running status |
| `GET /api/availability?train=12345&source=NDLS&destination=CNB&journeyDate=YYYY-MM-DD&classCode=3A&quotaCode=GN` | Seat availability |
| `GET /api/vacancy` | Explicitly reports berth-map data limitation |

## Next production steps

1. Confirm the current RailRadar API contract and supported response shapes against provider documentation.
2. Configure a valid key and test every endpoint against real provider responses.
3. Add provider-response fixtures for station/train schema variants.
4. Only implement exact segment berth mapping after an authorized source supplies that data.
5. Add rate limiting, request caching, monitoring, and deployment smoke tests before public launch.
