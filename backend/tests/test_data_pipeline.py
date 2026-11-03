import unittest
from io import BytesIO
from datetime import datetime, timedelta
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.data import (
    Cache,
    EvidenceStore,
    ExtractionFailure,
    FetchedPage,
    PublicDataRetriever,
    RetrievalReport,
    RetrievedSource,
    UnsafeURLError,
    extract_source,
    extract_source_detailed,
)
from app.db.models import Analysis, DocumentExtractionFailure, Evidence
from app.db.session import Base, get_db
from app.main import app


class FakeFetcher:
    def __init__(self, pages, *, robots_failure=None):
        self.pages = pages
        self.robots_failure = robots_failure
        self.calls = []

    def __call__(self, url):
        self.calls.append(url)
        if url.endswith("/robots.txt") and self.robots_failure:
            return self.robots_failure
        if url.endswith("/robots.txt") and url not in self.pages:
            return FetchedPage(status_code=404, final_url=url)
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


def make_pdf(text):
    """Build a small PDF fixture with one Helvetica text page."""
    text_bytes = text.encode("ascii")
    stream = b"BT /F1 12 Tf 40 200 Td (" + text_bytes + b") Tj ET"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 300] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n"
        + stream + b"\nendstream",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, body in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{number} 0 obj\n".encode("ascii"))
        pdf.extend(body)
        pdf.extend(b"\nendobj\n")
    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )
    return bytes(pdf)


def pdf_source(content, url="https://acme.example/annual-report.pdf"):
    return RetrievedSource(
        url=url,
        final_url=url,
        status_code=200,
        content_type="application/pdf",
        content=content.decode("latin-1"),
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
        self.assertEqual(
            fetcher.calls,
            ["https://acme.example/robots.txt", root, about, privacy],
        )

    def test_rejects_private_and_local_hosts(self):
        retriever = PublicDataRetriever(fetcher=FakeFetcher({}))

        with self.assertRaises(UnsafeURLError):
            retriever.retrieve("http://127.0.0.1/")
        with self.assertRaises(UnsafeURLError):
            retriever.retrieve("http://localhost:8000/")
        with self.assertRaises(UnsafeURLError):
            retriever.retrieve("file:///etc/passwd")
        with self.assertRaises(UnsafeURLError):
            retriever.retrieve("https://acme.example:8080/")

    def test_rejects_hostname_that_resolves_to_private_address(self):
        from app.data.retrieval import _validate_public_host

        private_answer = (2, 1, 6, "", ("10.0.0.8", 0))
        with patch("app.data.retrieval.socket.getaddrinfo", return_value=[private_answer]):
            with self.assertRaises(UnsafeURLError):
                _validate_public_host("company.example", resolve_dns=True)

    def test_revalidates_redirect_before_following_it(self):
        retriever = PublicDataRetriever()
        with patch.object(
            retriever,
            "_request_pinned",
            return_value=FetchedPage(
                status_code=302,
                final_url="https://company.example/",
                redirect_location="http://169.254.169.254/latest/meta-data/",
            ),
        ) as request:
            with self.assertRaises(UnsafeURLError):
                retriever._fetch_page("https://company.example/")

        request.assert_called_once()

    def test_dns_failure_fails_closed(self):
        with patch(
            "app.data.retrieval.socket.getaddrinfo",
            side_effect=__import__("socket").gaierror("DNS unavailable"),
        ):
            with self.assertRaises(UnsafeURLError):
                PublicDataRetriever()._request_pinned(
                    "https://unresolvable.example/"
                )

    def test_private_dns_answer_is_rejected_before_connecting(self):
        private_answer = (2, 1, 6, "", ("10.0.0.8", 443))
        with patch(
            "app.data.retrieval.socket.getaddrinfo",
            return_value=[private_answer],
        ), patch("app.data.retrieval.socket.socket") as socket_factory:
            with self.assertRaises(UnsafeURLError):
                PublicDataRetriever()._request_pinned("https://acme.example/")

        socket_factory.assert_not_called()

    def test_retrieval_accepts_pdf_mime_and_signature(self):
        root = "https://acme.example/"
        pdf_url = "https://acme.example/annual-report.pdf"
        binary_pdf_url = "https://acme.example/report-document"
        pdf = make_pdf(
            "Annual report revenue increased during the year and operations "
            "generated positive operating cash flow for investors."
        )
        fetcher = FakeFetcher(
            {
                root: make_page(
                    root,
                    '<a href="/annual-report.pdf">Annual report</a>'
                    '<a href="/report-document">Document</a>',
                ),
                pdf_url: make_page(pdf_url, pdf.decode("latin-1"), "application/pdf"),
                binary_pdf_url: make_page(
                    binary_pdf_url,
                    pdf.decode("latin-1"),
                    "application/octet-stream",
                ),
            }
        )

        report = PublicDataRetriever(fetcher=fetcher).retrieve(root)

        self.assertEqual(
            [source.final_url for source in report.sources],
            [root, pdf_url, binary_pdf_url],
        )
        self.assertEqual(report.sources[1].content_type, "application/pdf")
        self.assertEqual(report.sources[2].content_type, "application/octet-stream")


class RobotsPolicyTests(DatabaseTestCase):
    def test_allows_paths_permitted_by_robots_and_skips_disallowed_paths(self):
        root = "https://acme.example/"
        allowed = "https://acme.example/about"
        denied = "https://acme.example/private/financials"
        fetcher = FakeFetcher(
            {
                "https://acme.example/robots.txt": make_page(
                    "https://acme.example/robots.txt",
                    "User-agent: *\nDisallow: /private/\n",
                    "text/plain",
                ),
                root: make_page(
                    root,
                    '<a href="/about">About</a>'
                    '<a href="/private/financials">Private</a>',
                ),
                allowed: make_page(allowed, "About Acme and its services."),
                denied: make_page(denied, "Should never be fetched."),
            }
        )

        report = PublicDataRetriever(fetcher=fetcher).retrieve(root)

        self.assertEqual([source.url for source in report.sources], [root, allowed])
        self.assertNotIn(denied, fetcher.calls)

    def test_robots_retrieval_failure_fails_closed(self):
        robots_url = "https://acme.example/robots.txt"
        fetcher = FakeFetcher({}, robots_failure=FetchedPage(503, robots_url))

        report = PublicDataRetriever(fetcher=fetcher).retrieve(
            "https://acme.example/"
        )

        self.assertEqual(report.sources, [])
        self.assertEqual(len(report.failures), 1)
        self.assertIn("robots.txt", report.failures[0].reason)

    def test_observes_robots_crawl_delay(self):
        root = "https://acme.example/"
        about = "https://acme.example/about"
        fetcher = FakeFetcher(
            {
                "https://acme.example/robots.txt": make_page(
                    "https://acme.example/robots.txt",
                    "User-agent: *\nCrawl-delay: 1\n",
                    "text/plain",
                ),
                root: make_page(root, '<a href="/about">About</a>'),
                about: make_page(about, "About Acme and the company."),
            }
        )

        with patch("app.data.retrieval.time.sleep") as sleep:
            report = PublicDataRetriever(fetcher=fetcher).retrieve(root)

        self.assertEqual(len(report.sources), 2)
        self.assertGreaterEqual(sleep.call_count, 1)

    def test_unsafe_robots_redirect_fails_closed(self):
        fetcher = FakeFetcher(
            {},
            robots_failure=FetchedPage(
                status_code=200,
                final_url="http://169.254.169.254/latest/meta-data/",
                content="User-agent: *\nAllow: /\n",
            ),
        )

        report = PublicDataRetriever(fetcher=fetcher).retrieve(
            "https://acme.example/"
        )

        self.assertEqual(report.sources, [])
        self.assertEqual(len(report.failures), 1)
        self.assertIn("robots.txt", report.failures[0].url)

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

    def test_extracts_pdf_text_and_page_references(self):
        source = pdf_source(
            make_pdf(
                "Acme annual report revenue increased during the year and "
                "operations generated positive operating cash flow. Investors "
                "can review audited statements for the reporting period."
            )
        )

        extracted = extract_source_detailed(source)

        self.assertNotIsInstance(extracted, ExtractionFailure)
        self.assertIn("revenue increased", extracted.raw_text)
        self.assertEqual(extracted.source_metadata["document_type"], "pdf")
        self.assertEqual(extracted.source_metadata["page_references"], [1])
        self.assertEqual(extracted.url, source.final_url)
        self.assertIsNone(extracted.publication_date)

    def test_empty_pdf_returns_structured_failure(self):
        result = extract_source_detailed(pdf_source(make_pdf("")))

        self.assertIsInstance(result, ExtractionFailure)
        self.assertEqual(result.error_category, "empty_pdf")
        self.assertEqual(result.failure_stage, "text_extraction")

    def test_encrypted_pdf_returns_structured_failure(self):
        from pypdf import PdfWriter

        writer = PdfWriter()
        writer.add_blank_page(width=300, height=300)
        writer.encrypt("fixture-password")
        output = BytesIO()
        writer.write(output)

        result = extract_source_detailed(pdf_source(output.getvalue()))

        self.assertIsInstance(result, ExtractionFailure)
        self.assertEqual(result.error_category, "encrypted_pdf")

    def test_malformed_pdf_returns_structured_failure(self):
        result = extract_source_detailed(pdf_source(b"%PDF-1.4 not a valid document"))

        self.assertIsInstance(result, ExtractionFailure)
        self.assertEqual(result.source_url, "https://acme.example/annual-report.pdf")
        self.assertIn(result.error_category, {"malformed_pdf", "empty_pdf"})
        self.assertTrue(result.description)

    def test_oversized_pdf_is_rejected_before_parsing(self):
        source = pdf_source(make_pdf("X" * 300))

        result = extract_source_detailed(source, max_document_bytes=100)

        self.assertIsInstance(result, ExtractionFailure)
        self.assertEqual(result.error_category, "document_too_large")


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

    def test_persists_structured_document_extraction_failures(self):
        analysis = self._analysis()
        store = EvidenceStore(self.db)
        startup = store.ensure_startup("Acme", analysis.website)
        failed_source = pdf_source(b"%PDF-1.4 malformed")
        prior_evidence = RetrievedSource(
            url=failed_source.final_url,
            final_url=failed_source.final_url,
            status_code=200,
            content_type="text/html",
            content=(
                "<html><body><p>"
                + "Acme publishes annual financial information for investors. " * 10
                + "</p></body></html>"
            ),
        )
        store.store_report(
            analysis,
            startup,
            RetrievalReport(sources=[prior_evidence]),
        )
        self.db.commit()
        self.assertEqual(self.db.query(Evidence).count(), 1)
        prior_record = self.db.query(Evidence).one()
        prior_id = prior_record.id
        prior_content = prior_record.extracted_information
        prior_raw_text = prior_record.raw_text
        prior_metadata = dict(prior_record.source_metadata)
        prior_hash = prior_record.content_hash
        prior_retrieval_date = prior_record.retrieval_date
        prior_title = prior_record.source_title
        prior_findings = list(prior_record.findings)

        report = RetrievalReport(sources=[failed_source])

        result = store.store_report(analysis, startup, report)
        self.db.commit()

        failure = (
            self.db.query(DocumentExtractionFailure)
            .filter_by(analysis_id=analysis.id, source_url=failed_source.final_url)
            .one()
        )
        self.assertEqual(result.skipped, 1)
        self.assertEqual(len(result.extraction_failures), 1)
        self.assertIn(
            failure.failure_stage,
            {"document_validation", "text_extraction"},
        )
        self.assertEqual(failure.error_category, "malformed_pdf")
        self.assertTrue(failure.description)
        self.assertEqual(self.db.query(Evidence).count(), 1)
        preserved = store.get(prior_id)
        self.assertIsNotNone(preserved)
        self.assertEqual(preserved.extracted_information, prior_content)
        self.assertEqual(preserved.raw_text, prior_raw_text)
        self.assertEqual(preserved.source_metadata, prior_metadata)
        self.assertEqual(preserved.content_hash, prior_hash)
        self.assertEqual(preserved.retrieval_date, prior_retrieval_date)
        self.assertEqual(preserved.source_title, prior_title)
        self.assertEqual(preserved.findings, prior_findings)
        self.assertEqual(store.search(analysis_id=analysis.id).total, 1)

        replacement_source = pdf_source(
            make_pdf(
                "Acme annual report revenue increased during the year, "
                "and the company reported positive operating cash flow. "
                "Investors can review the statements for this period."
            )
        )
        replacement_result = store.store_report(
            analysis,
            startup,
            RetrievalReport(sources=[replacement_source]),
        )
        self.db.commit()

        updated = store.get(prior_id)
        self.assertEqual(replacement_result.updated, 1)
        self.assertIsNotNone(updated)
        self.assertEqual(updated.id, prior_id)
        self.assertEqual(updated.source_metadata["document_type"], "pdf")
        self.assertNotEqual(updated.content_hash, prior_hash)
        self.assertEqual(
            self.db.query(DocumentExtractionFailure)
            .filter_by(analysis_id=analysis.id, source_url=failed_source.final_url)
            .count(),
            0,
        )

    def test_initial_extraction_failure_is_recorded_without_evidence(self):
        analysis = self._analysis()
        store = EvidenceStore(self.db)
        startup = store.ensure_startup("Acme", analysis.website)
        source = pdf_source(b"%PDF-1.4 malformed")

        store.store_report(
            analysis,
            startup,
            RetrievalReport(sources=[source]),
        )
        self.db.commit()

        self.assertEqual(self.db.query(Evidence).count(), 0)
        self.assertEqual(
            self.db.query(DocumentExtractionFailure)
            .filter_by(analysis_id=analysis.id, source_url=source.final_url)
            .count(),
            1,
        )


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
