import unittest
from unittest.mock import Mock, patch

import app as railway_app


class RailwayFinderTests(unittest.TestCase):
    def setUp(self):
        railway_app.app.config["TESTING"] = True
        self.client = railway_app.app.test_client()
        self.key_patcher = patch.object(railway_app, "API_KEY", "test-key")
        self.key_patcher.start()
        self.addCleanup(self.key_patcher.stop)

    def test_homepage_loads(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Railway Finder", response.data)

    def test_health_reports_missing_key(self):
        with patch.object(railway_app, "API_KEY", ""):
            response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 503)
        self.assertFalse(response.get_json()["ok"])

    def test_station_search_short_query_does_not_call_provider(self):
        with patch.object(railway_app, "provider_get") as provider:
            response = self.client.get("/api/stations?q=a")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["stations"], [])
        provider.assert_not_called()

    def test_train_route_requires_station_codes(self):
        response = self.client.get("/api/trains?source=Delhi&destination=CNB")
        self.assertEqual(response.status_code, 400)

    def test_train_route_rejects_same_station(self):
        response = self.client.get("/api/trains?source=CNB&destination=CNB")
        self.assertEqual(response.status_code, 400)

    def test_valid_train_route_returns_provider_trains(self):
        payload = {"data": {"from": {"code": "NDLS"}, "to": {"code": "CNB"}, "trains": [{"number": "12345"}]}}
        with patch.object(railway_app, "provider_get", return_value=(payload, 200)):
            response = self.client.get("/api/trains?source=NDLS&destination=CNB&date=2026-10-10")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["trains"][0]["number"], "12345")

    def test_availability_validates_date(self):
        response = self.client.get("/api/availability?train=12345&source=NDLS&destination=CNB&journeyDate=not-a-date")
        self.assertEqual(response.status_code, 400)

    def test_availability_validates_class(self):
        response = self.client.get("/api/availability?train=12345&source=NDLS&destination=CNB&journeyDate=2026-10-10&classCode=BAD")
        self.assertEqual(response.status_code, 400)

    def test_provider_error_is_returned_as_json(self):
        with patch.object(railway_app, "provider_get", return_value=({"error": "provider unavailable"}, 502)):
            response = self.client.get("/api/status/12345")
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.get_json()["error"], "provider unavailable")

    def test_vacancy_is_not_fabricated(self):
        response = self.client.get("/api/vacancy")
        self.assertEqual(response.status_code, 501)
        self.assertFalse(response.get_json()["exact_segment_berth_data"])


if __name__ == "__main__":
    unittest.main()
