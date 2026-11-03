import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.data import (
    Cache,
    EvidenceStore,
    FetchedPage,
    PublicDataRetriever,
    RetrievalReport,
    RetrievedSource,
    UnsafeURLError,
    extract_source,
)
from app.db.models import Analysis, Evidence
from app.db.session import Base, get_db
from app.main import app


class FakeFetcher:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def __call__(self, url):
        self.calls.append(url)
        if url not in self.pages:
            raise RuntimeError(f"unexpected URL: {url}")
        return self.pages[url]


def make_page(url, content, content_type="text/html"):
    return FetchedPage(
        status_code=200,
        final_url=url,
        content_type=content_type,
        content=content,
    )


class DatabaseTestCase(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()


class RetrievalTests(DatabaseTestCase):
    def test_retrieves_root_and_high_signal_same_host_pages(self):
        root = "https://acme.example/"
        about = "https://acme.example/about"
        privacy = "https://acme.example/privacy"
        pages = {
            root: make_page(
                root,
                """
                <html><body>
                <a href="/about">About</a>
                <a href="/privacy">Privacy</a>
                <a href="https://outside.example/about">Outside</a>
                <a href="/logo.png">Logo</a>
                </body></html>
                """,
            ),
            about: make_page(about, "<html><body>About Acme</body></html>"),
            privacy: make_page(privacy, "<html><body>Privacy</body></html>"),
        }
        fetcher = FakeFetcher(pages)
        retriever = PublicDataRetriever(fetcher=fetcher, max_pages=3)

        report = retriever.retrieve(root, max_pages=3)

        self.assertEqual([source.url for source in report.sources], [
            root,
            about,
            privacy,
        ])
        self.assertEqual(report.failures, [])
        self.assertEqual(fetcher.calls, [root, about, privacy])

    def test_rejects_private_and_local_hosts(self):
        retriever = PublicDataRetriever(fetcher=FakeFetcher({}))

        with self.assertRaises(UnsafeURLError):
            retriever.retrieve("http://127.0.0.1/")
        with self.assertRaises(UnsafeURLError):
            retriever.retrieve("http://localhost:8000/")
        with self.assertRaises(UnsafeURLError):
            retriever.retrieve("file:///etc/passwd")

    def test_uses_cache_for_repeated_retrieval(self):
        root = "https://acme.example/"
        about = "https://acme.example/about"
        pages = {
            root: make_page(
                root,
                '<html><body><a href="/about">About</a></body></html>',
            ),
            about: make_page(about, "<html><body>About Acme</body></html>"),
        }
        first_fetcher = FakeFetcher(pages)
        first = PublicDataRetriever(
            cache=Cache(self.db),
            fetcher=first_fetcher,
            max_pages=2,
        )
        first_report = first.retrieve(root, max_pages=2)
        self.assertEqual(len(first_report.sources), 2)

        second_fetcher = FakeFetcher({})
        second = PublicDataRetriever(
            cache=Cache(self.db),
            fetcher=second_fetcher,
            max_pages=2,
        )
        second_report = second.retrieve(root, max_pages=2)

        self.assertEqual(len(second_report.sources), 2)
        self.assertTrue(all(source.from_cache for source in second_report.sources))
        self.assertEqual(second_fetcher.calls, [])

    def test_expired_cache_entry_is_discarded(self):
        cache = Cache(self.db, success_ttl_seconds=60)
        entry = cache.set(
            "https://acme.example/",
            final_url="https://acme.example/",
            status_code=200,
            content="hello",
        )
        entry.expires_at = datetime.utcnow() - timedelta(seconds=1)
        self.db.commit()

        self.assertIsNone(cache.get("https://acme.example/"))


class ExtractionTests(unittest.TestCase):
    def test_extracts_verbatim_metadata_and_respects_category(self):
        source = RetrievedSource(
            url="https://acme.example/privacy",
            final_url="https://acme.example/privacy",
            status_code=200,
            content_type="text/html",
            content="""
            <html>
              <head>
                <title>Acme - Privacy Policy</title>
                <meta name="description" content="How Acme handles customer data.">
                <meta property="article:published_time" content="2026-02-03T10:30:00Z">
              </head>
              <body>
                <nav>Home Pricing</nav>
                <main>
                  <h1>Privacy Policy</h1>
                  <p>We collect only the information needed to provide our service.</p>
                  <p>Customers can request deletion of their data at any time.</p>
                </main>
                <script>this should not appear</script>
              </body>
            </html>
            """,
        )

        extracted = extract_source(source)

        self.assertIsNotNone(extracted)
        self.assertEqual(extracted.source_title, "Acme - Privacy Policy")
        self.assertEqual(extracted.source_category, "legal")
        self.assertEqual(extracted.related_agent, "legal_compliance_agent")
        self.assertIn("How Acme handles customer data.", extracted.extracted_information)
        self.assertIn("Customers can request deletion", extracted.extracted_information)
        self.assertNotIn("this should not appear", extracted.raw_text)
        self.assertEqual(extracted.publication_date, datetime(2026, 2, 3, 10, 30))
        self.assertTrue(extracted.content_hash)

    def test_unusable_page_is_not_turned_into_evidence(self):
        source = RetrievedSource(
            url="https://acme.example/short",
            final_url="https://acme.example/short",
            status_code=200,
            content_type="text/html",
            content="<html><head><title>Short</title></head><body>tiny</body></html>",
        )

        self.assertIsNone(extract_source(source))


class EvidenceStoreTests(DatabaseTestCase):
    def _analysis(self):
        analysis = Analysis(
            startup_name="Acme",
            website="https://acme.example/",
            industry="Software",
            status="pending",
        )
        self.db.add(analysis)
        self.db.commit()
        self.db.refresh(analysis)
        return analysis

    def _report(self):
        return RetrievalReport(
            sources=[
                RetrievedSource(
                    url="https://acme.example/about",
                    final_url="https://acme.example/about",
                    status_code=200,
                    content_type="text/html",
                    content="""
                    <html><head>
                    <title>About Acme</title>
                    <meta name="description" content="Acme builds workflow software for finance teams.">
                    </head><body>
                    <p>Acme builds workflow software for finance teams.</p>
                    </body></html>
                    """,
                ),
                RetrievedSource(
                    url="https://acme.example/empty",
                    final_url="https://acme.example/empty",
                    status_code=200,
                    content_type="text/html",
                    content="<html><body>tiny</body></html>",
                ),
            ]
        )

    def test_stores_only_usable_sources_and_upserts(self):
        analysis = self._analysis()
        store = EvidenceStore(self.db)
        startup = store.ensure_startup(
            analysis.startup_name,
            analysis.website,
            industry=analysis.industry,
        )
        self.assertEqual(
            store.ensure_startup("Acme", "acme.example").id,
            startup.id,
        )

        result = store.store_report(analysis, startup, self._report())
        self.db.commit()

        self.assertEqual(result.total_sources, 2)
        self.assertEqual(result.stored, 1)
        self.assertEqual(result.skipped, 1)
        self.assertEqual(self.db.query(Evidence).count(), 1)

        again = store.store_report(analysis, startup, self._report())
        self.db.commit()

        self.assertEqual(again.stored, 0)
        self.assertEqual(again.updated, 1)
        self.assertEqual(self.db.query(Evidence).count(), 1)

        search = store.search(query="workflow")
        self.assertEqual(search.total, 1)
        self.assertEqual(search.items[0].verification_status, "unverified")
        self.assertEqual(search.items[0].source_category, "company")


class EvidenceApiTests(DatabaseTestCase):
    def setUp(self):
        super().setUp()
        self.analysis = Analysis(
            startup_name="Acme",
            website="https://acme.example/",
            industry="Software",
            status="pending",
        )
        self.db.add(self.analysis)
        self.db.commit()
        self.db.refresh(self.analysis)

        def override_db():
            yield self.db

        app.dependency_overrides[get_db] = override_db
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        super().tearDown()

    def test_collect_search_and_get_evidence(self):
        report = RetrievalReport(
            sources=[
                RetrievedSource(
                    url="https://acme.example/about",
                    final_url="https://acme.example/about",
                    status_code=200,
                    content_type="text/html",
                    content="""
                    <html><head>
                    <title>About Acme</title>
                    <meta name="description" content="Acme builds workflow software for finance teams.">
                    </head><body>
                    <p>Acme builds workflow software for finance teams.</p>
                    </body></html>
                    """,
                )
            ]
        )

        with patch.object(PublicDataRetriever, "retrieve", return_value=report):
            response = self.client.post(
                f"/api/v1/analyses/{self.analysis.id}/collect-evidence",
                params={"max_pages": 2},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["stored_evidence"], 1)

        search = self.client.get(
            "/api/v1/evidence",
            params={"analysis_id": self.analysis.id, "q": "Acme"},
        )
        self.assertEqual(search.status_code, 200)
        payload = search.json()
        self.assertEqual(payload["total"], 1)
        evidence_id = payload["items"][0]["id"]

        detail = self.client.get(f"/api/v1/evidence/{evidence_id}")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["verification_status"], "unverified")

        missing = self.client.get("/api/v1/evidence/999999")
        self.assertEqual(missing.status_code, 404)
