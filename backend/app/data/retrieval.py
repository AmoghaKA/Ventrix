import ipaddress
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Callable, List, Optional, Sequence
from urllib.parse import urljoin, urlsplit, urlunsplit

import httpx

from app.data.cache import Cache


class UnsafeURLError(ValueError):
    """Raised when a URL is malformed or points at a non-public host."""


@dataclass(frozen=True)
class FetchedPage:
    status_code: int
    final_url: str
    content_type: str = ""
    content: str = ""


@dataclass(frozen=True)
class RetrievedSource:
    url: str
    final_url: str
    status_code: int
    content_type: str
    content: str
    from_cache: bool = False


@dataclass(frozen=True)
class RetrievalFailure:
    url: str
    reason: str


@dataclass
class RetrievalReport:
    sources: List[RetrievedSource] = field(default_factory=list)
    failures: List[RetrievalFailure] = field(default_factory=list)


Fetcher = Callable[[str], FetchedPage]

_SKIPPED_EXTENSIONS = (
    ".7z",
    ".avi",
    ".css",
    ".doc",
    ".docx",
    ".gif",
    ".gz",
    ".ico",
    ".jpeg",
    ".jpg",
    ".js",
    ".json",
    ".mov",
    ".mp3",
    ".mp4",
    ".pdf",
    ".png",
    ".ppt",
    ".pptx",
    ".rar",
    ".svg",
    ".tar",
    ".webm",
    ".webp",
    ".woff",
    ".woff2",
    ".xls",
    ".xlsx",
    ".xml",
    ".zip",
)

_LINK_SCORES = {
    "about": 12,
    "company": 10,
    "team": 10,
    "founder": 9,
    "product": 8,
    "solution": 8,
    "pricing": 9,
    "customer": 9,
    "case": 8,
    "investor": 9,
    "funding": 9,
    "financial": 9,
    "press": 7,
    "news": 7,
    "media": 6,
    "blog": 5,
    "legal": 7,
    "terms": 7,
    "privacy": 7,
    "compliance": 7,
    "contact": 3,
    "career": 2,
}

_NEGATIVE_LINK_TERMS = (
    "login",
    "signin",
    "sign-in",
    "signup",
    "sign-up",
    "cart",
    "checkout",
    "wp-admin",
    "share=",
)


class _AnchorParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: List[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() != "a":
            return
        for name, value in attrs:
            if name.lower() == "href" and value:
                self.links.append(value.strip())
                break


def normalize_request_url(website: str) -> str:
    value = (website or "").strip()
    if not value:
        raise UnsafeURLError("A website URL is required")

    if "://" not in value:
        value = f"https://{value}"

    parsed = urlsplit(value)
    scheme = parsed.scheme.lower()
    if scheme not in {"http", "https"}:
        raise UnsafeURLError("Only http and https URLs are supported")
    if not parsed.hostname:
        raise UnsafeURLError("The website URL is missing a hostname")
    if parsed.username or parsed.password:
        raise UnsafeURLError("URLs containing credentials are not supported")

    _validate_public_host(parsed.hostname)

    netloc = parsed.netloc.lower()
    path = parsed.path or "/"
    return urlunsplit((scheme, netloc, path, parsed.query, ""))


def _validate_public_host(hostname: str) -> None:
    host = hostname.rstrip(".").lower()

    if host in {"localhost", "localhost.localdomain"} or host.endswith(".localhost"):
        raise UnsafeURLError("Local hosts cannot be retrieved")
    if host.endswith(".local") or host.endswith(".internal"):
        raise UnsafeURLError("Internal hosts cannot be retrieved")

    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return

    if (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_reserved
        or address.is_multicast
        or address.is_unspecified
    ):
        raise UnsafeURLError("Private or non-public IP addresses cannot be retrieved")


class PublicDataRetriever:
    """Retrieve publicly accessible HTML from a startup website.

    The retriever intentionally limits itself to the startup's own host and a
    small number of high-signal pages. It never treats a failed or empty fetch
    as evidence.
    """

    def __init__(
        self,
        cache: Optional[Cache] = None,
        fetcher: Optional[Fetcher] = None,
        *,
        timeout_seconds: float = 12.0,
        max_pages: int = 5,
        max_bytes: int = 2_000_000,
        user_agent: str = "VentrixResearchBot/0.1 (+public due-diligence research)",
    ) -> None:
        self.cache = cache
        self.fetcher = fetcher
        self.timeout_seconds = timeout_seconds
        self.max_pages = max(1, max_pages)
        self.max_bytes = max_bytes
        self.user_agent = user_agent

    def retrieve(
        self,
        website: str,
        *,
        max_pages: Optional[int] = None,
    ) -> RetrievalReport:
        root_url = normalize_request_url(website)
        page_limit = max(1, min(max_pages or self.max_pages, self.max_pages))
        report = RetrievalReport()

        root_source, root_failure = self._fetch(root_url)
        if root_failure:
            report.failures.append(root_failure)
            return report

        report.sources.append(root_source)
        if page_limit == 1:
            return report

        links = self._discover_links(root_source.content, root_source.final_url)
        attempted = {root_url, root_source.final_url}

        for link in links:
            if len(report.sources) + len(report.failures) >= page_limit:
                break
            if link in attempted:
                continue
            attempted.add(link)

            source, failure = self._fetch(link)
            if source:
                report.sources.append(source)
            elif failure:
                report.failures.append(failure)

        return report

    def _fetch(self, url: str):
        if self.cache:
            cached = self.cache.get(url)
            if cached:
                if cached.error:
                    return None, RetrievalFailure(url, cached.error)
                if cached.status_code is not None and cached.status_code >= 400:
                    return None, RetrievalFailure(
                        url,
                        f"HTTP {cached.status_code}",
                    )
                return (
                    RetrievedSource(
                        url=url,
                        final_url=cached.final_url or url,
                        status_code=cached.status_code or 200,
                        content_type=cached.content_type or "",
                        content=cached.content or "",
                        from_cache=True,
                    ),
                    None,
                )

        try:
            page = self._fetch_page(url)
        except Exception as exc:
            reason = f"Fetch failed: {exc}"
            if self.cache:
                self.cache.set(url, error=reason)
            return None, RetrievalFailure(url, reason)

        try:
            final_url = normalize_request_url(page.final_url or url)
        except UnsafeURLError as exc:
            reason = f"Unsafe redirect: {exc}"
            if self.cache:
                self.cache.set(url, error=reason)
            return None, RetrievalFailure(url, reason)

        if page.status_code >= 400:
            reason = f"HTTP {page.status_code}"
            if self.cache:
                self.cache.set(
                    url,
                    final_url=final_url,
                    status_code=page.status_code,
                    error=reason,
                )
            return None, RetrievalFailure(url, reason)

        if page.status_code < 200 or page.status_code >= 300:
            reason = f"Unexpected HTTP status {page.status_code}"
            if self.cache:
                self.cache.set(
                    url,
                    final_url=final_url,
                    status_code=page.status_code,
                    error=reason,
                )
            return None, RetrievalFailure(url, reason)

        content_type = (page.content_type or "").split(";", 1)[0].strip().lower()
        allowed_types = {"text/html", "application/xhtml+xml", "text/plain"}
        if content_type and content_type not in allowed_types:
            reason = f"Unsupported content type: {content_type}"
            if self.cache:
                self.cache.set(
                    url,
                    final_url=final_url,
                    status_code=page.status_code,
                    content_type=content_type,
                    error=reason,
                )
            return None, RetrievalFailure(url, reason)

        if len(page.content.encode("utf-8")) > self.max_bytes:
            reason = "Response exceeded the maximum allowed size"
            if self.cache:
                self.cache.set(
                    url,
                    final_url=final_url,
                    status_code=page.status_code,
                    content_type=content_type,
                    error=reason,
                )
            return None, RetrievalFailure(url, reason)

        if self.cache:
            self.cache.set(
                url,
                final_url=final_url,
                status_code=page.status_code,
                content_type=content_type,
                content=page.content,
            )

        return (
            RetrievedSource(
                url=url,
                final_url=final_url,
                status_code=page.status_code,
                content_type=content_type,
                content=page.content,
            ),
            None,
        )

    def _fetch_page(self, url: str) -> FetchedPage:
        if self.fetcher is not None:
            return self.fetcher(url)

        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,text/plain;q=0.8",
        }
        with httpx.Client(
            follow_redirects=True,
            timeout=self.timeout_seconds,
            headers=headers,
        ) as client:
            response = client.get(url)
            return FetchedPage(
                status_code=response.status_code,
                final_url=str(response.url),
                content_type=response.headers.get("content-type", ""),
                content=response.text,
            )

    def _discover_links(self, html: str, base_url: str) -> Sequence[str]:
        parser = _AnchorParser()
        try:
            parser.feed(html)
        except Exception:
            return []

        base_host = urlsplit(base_url).hostname
        if not base_host:
            return []

        seen = {normalize_request_url(base_url)}
        scored: List[tuple[int, int, str]] = []

        for index, href in enumerate(parser.links):
            href = href.strip()
            if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
                continue

            absolute = urljoin(base_url, href)
            parsed = urlsplit(absolute)
            if parsed.scheme.lower() not in {"http", "https"}:
                continue
            if parsed.hostname != base_host:
                continue

            path = parsed.path.lower()
            if path.endswith(_SKIPPED_EXTENSIONS):
                continue

            try:
                candidate = normalize_request_url(absolute)
            except UnsafeURLError:
                continue

            if candidate in seen:
                continue
            seen.add(candidate)

            hint = f"{parsed.path}?{parsed.query}".lower()
            if any(term in hint for term in _NEGATIVE_LINK_TERMS):
                continue

            score = sum(
                points for term, points in _LINK_SCORES.items() if term in hint
            )
            scored.append((score, index, candidate))

        scored.sort(key=lambda item: (-item[0], item[1]))
        return [candidate for _, _, candidate in scored]
