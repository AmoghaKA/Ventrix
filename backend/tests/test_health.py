"""Health endpoint tests."""

import unittest

from app.main import app
from fastapi.testclient import TestClient


class HealthTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "healthy")

    def test_db_test(self):
        response = self.client.get("/db-test")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["database"], "connected")
