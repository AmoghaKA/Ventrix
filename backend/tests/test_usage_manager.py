import threading
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import Base
from app.services.usage_manager import UsageLimitExceeded, UsageLimitManager


class UsageManagerTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def tearDown(self):
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_success_increments_completed(self):
        db = self.Session()
        manager = UsageLimitManager(max_analyses=2)
        manager.reserve_analysis(db)
        manager.complete_analysis(db, success=True)
        usage = manager.get_usage(db)
        self.assertEqual(usage["completed_analyses"], 1)
        self.assertEqual(usage["remaining_analyses"], 1)
        db.close()

    def test_failure_does_not_count(self):
        db = self.Session()
        manager = UsageLimitManager(max_analyses=2)
        manager.reserve_analysis(db)
        manager.complete_analysis(db, success=False)
        usage = manager.get_usage(db)
        self.assertEqual(usage["completed_analyses"], 0)
        self.assertEqual(usage["reserved_analyses"], 0)
        db.close()

    def test_limit_reached(self):
        db = self.Session()
        manager = UsageLimitManager(max_analyses=1)
        manager.reserve_analysis(db)
        manager.complete_analysis(db, success=True)
        with self.assertRaises(UsageLimitExceeded):
            manager.reserve_analysis(db)
        db.close()

    def test_simultaneous_requests_do_not_exceed(self):
        manager = UsageLimitManager(max_analyses=1)
        results = []

        def worker():
            db = self.Session()
            try:
                manager.reserve_analysis(db)
                manager.complete_analysis(db, success=True)
                results.append("ok")
            except UsageLimitExceeded:
                results.append("blocked")
            finally:
                db.close()

        t1 = threading.Thread(target=worker)
        t2 = threading.Thread(target=worker)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        self.assertEqual(sorted(results), ["blocked", "ok"])
        db = self.Session()
        self.assertEqual(manager.get_usage(db)["completed_analyses"], 1)
        db.close()


if __name__ == "__main__":
    unittest.main()
