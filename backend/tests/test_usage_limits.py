"""Tests for the configured analysis usage limit."""

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import Analysis, Base
from app.db.session import get_db
from app.main import app
from fastapi.testclient import TestClient


class UsageLimitTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

        def override_db():
            yield self.db

        app.dependency_overrides[get_db] = override_db
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_analysis_limit_is_enforced(self):
        for index in range(10):
            response = self.client.post(
                "/api/v1/analyses",
                json={
                    "startup_name": f"Company {index}",
                    "website": f"https://company{index}.example",
                },
            )
            self.assertEqual(response.status_code, 201, response.text)

        blocked = self.client.post(
            "/api/v1/analyses",
            json={
                "startup_name": "Blocked Company",
                "website": "https://blocked.example",
            },
        )

        self.assertEqual(blocked.status_code, 403)
        self.assertIn("Maximum analysis limit", blocked.json()["detail"])


if __name__ == "__main__":
    unittest.main()
