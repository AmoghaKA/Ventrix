import http.client
import ipaddress
import socket
import ssl
import time
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Callable, List, Optional, Sequence
from urllib.parse import quote, urljoin, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

from app.data.cache import Cache


class UnsafeURLError(ValueError):
    """Raised when a URL is malformed or points at a non-public host."""


@dataclass(frozen=True)
class FetchedPage:
    status_code: int
    final_url: str
    content_type: str = ""
    content: str = ""
    redirect_location: Optional[str] = None


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
    if any(ord(character) < 0x20 or ord(character) == 0x7F for character in value):
        raise UnsafeURLError("Control characters are not allowed in website URLs")

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
    try:
        port = parsed.port
    except ValueError as exc:
        raise UnsafeURLError("The website URL contains an invalid port") from exc
    if port == 0:
        raise UnsafeURLError("Port 0 is not a valid website port")
    expected_port = 443 if scheme == "https" else 80
    if port is not None and port != expected_port:
        raise UnsafeURLError("Only standard public web ports are supported")

    _validate_public_host(parsed.hostname)

    netloc = parsed.netloc.lower()
    path = parsed.path or "/"
    return urlunsplit((scheme, netloc, path, parsed.query, ""))


def _validate_public_host(hostname: str, *, resolve_dns: bool = False) -> None:
    host = hostname.rstrip(".").lower()

    if host in {"localhost", "localhost.localdomain"} or host.endswith(".localhost"):
        raise UnsafeURLError("Local hosts cannot be retrieved")
    if host.endswith(".local") or host.endswith(".internal"):
        raise UnsafeURLError("Internal hosts cannot be retrieved")

    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        if not resolve_dns:
            return
        _resolve_public_host(host, None)
        return

    if not address.is_global:
        raise UnsafeURLError("Private or non-public IP addresses cannot be retrieved")


def _resolve_public_host(hostname: str, port: Optional[int]):
    """Resolve once, reject mixed/private answers, and return pinned addresses."""
    try:
        results = socket.getaddrinfo(
            hostname,
            port,
            type=socket.SOCK_STREAM,
        )
        addresses = [ipaddress.ip_address(result[4][0]) for result in results]
    except (OSError, ValueError, IndexError) as exc:
        raise UnsafeURLError("The website hostname could not be resolved") from exc
    if not results:
        raise UnsafeURLError("The website hostname could not be resolved")
    # Reject the host when any answer is non-public; a public answer cannot
    # mask a private address returned in the same DNS response.
    if any(not address.is_global for address in addresses):
        raise UnsafeURLError("Private or non-public IP addresses cannot be retrieved")
    return results


class PublicDataRetriever:
    """Retrieve public pages while enforcing a conservative robots policy.

    A valid robots.txt is evaluated with Python's RFC-style parser. A 404 means
    no policy was published and permits crawling. Every other robots retrieval
    or parsing failure blocks crawling for that origin. Redirects and DNS are
    handled by the same pinned public-HTTP path used for pages.
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
        max_redirects: int = 5,
    ) -> None:
        self.cache = cache
        self.fetcher = fetcher
        self.timeout_seconds = timeout_seconds
        self.max_pages = max(1, max_pages)
        self.max_bytes = max_bytes
        self.user_agent = user_agent
        self.max_redirects = max(0, max_redirects)

    def retrieve(
        self,
        website: str,
        *,
        max_pages: Optional[int] = None,
    ) -> RetrievalReport:
        root_url = normalize_request_url(website)
        page_limit = max(1, min(max_pages or self.max_pages, self.max_pages))
        report = RetrievalReport()

        robots, robots_failure = self._load_robots(root_url)
        if robots_failure:
            report.failures.append(robots_failure)
            return report
        if robots is not None and not robots.can_fetch(self.user_agent, root_url):
            report.failures.append(
                RetrievalFailure(root_url, "Blocked by the site's robots.txt policy")
            )
            return report

        last_request_at = time.monotonic()
        self._wait_for_robots_rate(robots, last_request_at)
        root_source, root_failure = self._fetch(root_url)
        last_request_at = time.monotonic()
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
            if robots is not None and not robots.can_fetch(self.user_agent, link):
                continue

            self._wait_for_robots_rate(robots, last_request_at)
            source, failure = self._fetch(link)
            last_request_at = time.monotonic()
            if source:
                report.sources.append(source)
            elif failure:
                report.failures.append(failure)

        return report

    def _wait_for_robots_rate(
        self,
        robots: Optional[RobotFileParser],
        last_request_at: float,
    ) -> None:
        if robots is None:
            return
        delays = []
        crawl_delay = robots.crawl_delay(self.user_agent)
        if crawl_delay is not None:
            delays.append(float(crawl_delay))
        request_rate = robots.request_rate(self.user_agent)
        if request_rate and request_rate.requests > 0:
            delays.append(float(request_rate.seconds) / request_rate.requests)
        delay = max(delays, default=0.0)
        remaining = delay - (time.monotonic() - last_request_at)
        if remaining > 0:
            time.sleep(remaining)

    def _load_robots(
        self,
        website_url: str,
    ) -> tuple[Optional[RobotFileParser], Optional[RetrievalFailure]]:
        parsed = urlsplit(website_url)
        robots_url = urlunsplit((parsed.scheme, parsed.netloc, "/robots.txt", "", ""))
        source, failure = self._fetch(robots_url)

        # RFC 9309 treats a 4xx response as unavailable. Ventrix adopts the
        # narrower 404 exception; authorization, rate-limit, server, network,
        # redirect, and parsing failures all fail closed.
        if failure:
            if failure.reason == "HTTP 404":
                parser = RobotFileParser(robots_url)
                parser.parse([])
                return parser, None
            return None, RetrievalFailure(
                robots_url,
                f"Crawling blocked because robots.txt could not be retrieved: {failure.reason}",
            )
        if source is None or source.status_code != 200:
            return None, RetrievalFailure(
                robots_url,
                "Crawling blocked because robots.txt returned an unusable response",
            )

        parser = RobotFileParser(robots_url)
        try:
            parser.parse(source.content.splitlines())
        except Exception:
            return None, RetrievalFailure(
                robots_url,
                "Crawling blocked because robots.txt could not be parsed",
            )
        return parser, None

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
        pdf_content = _page_contains_pdf(page)
        if content_type == "application/pdf" or (
            content_type == "application/octet-stream" and pdf_content
        ):
            pass
        elif content_type and content_type not in allowed_types:
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

        content_size = len(page.content.encode("utf-8", errors="replace"))
        if pdf_content:
            content_size = len(page.content.encode("latin-1", errors="replace"))
        if content_size > self.max_bytes:
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

        current_url = normalize_request_url(url)
        for redirect_count in range(self.max_redirects + 1):
            page = self._request_pinned(current_url)
            if not page.redirect_location:
                return page
            if redirect_count >= self.max_redirects:
                raise ValueError("The page exceeded the redirect limit")
            # The next hop is normalized and DNS-pinned by _request_pinned
            # before a socket is opened for it.
            current_url = normalize_request_url(
                urljoin(current_url, page.redirect_location)
            )

        raise ValueError("The page exceeded the redirect limit")

    def _request_pinned(self, url: str) -> FetchedPage:
        """Fetch one URL while connecting only to a validated DNS address.

        The socket connects to an IP from the validated DNS answer directly,
        while TLS SNI and the HTTP Host header retain the original hostname.
        This closes the DNS check/connect rebinding window.
        """
        parsed = urlsplit(normalize_request_url(url))
        hostname = parsed.hostname or ""
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        results = _resolve_public_host(hostname, port)

        request_path = quote(parsed.path or "/", safe="/%:@!$&'()*+,;=-._~")
        if parsed.query:
            request_path += "?" + quote(parsed.query, safe="/?@!$&'()*+,;=:%-._~")
        host_header = f"[{hostname}]" if ":" in hostname else hostname
        if port != (443 if parsed.scheme == "https" else 80):
            host_header = f"{host_header}:{port}"

        last_error: Optional[OSError] = None
        for family, socktype, protocol, _, sockaddr in results:
            raw_socket = socket.socket(family, socktype, protocol)
            raw_socket.settimeout(self.timeout_seconds)
            connection = raw_socket
            try:
                raw_socket.connect(sockaddr)
                if parsed.scheme == "https":
                    connection = ssl.create_default_context().wrap_socket(
                        raw_socket,
                        server_hostname=hostname,
                    )
                request = (
                    f"GET {request_path} HTTP/1.1\r\n"
                    f"Host: {host_header}\r\n"
                    f"User-Agent: {self.user_agent}\r\n"
                    "Accept: text/html,application/xhtml+xml,text/plain;q=0.8\r\n"
                    "Accept-Encoding: identity\r\n"
                    "Connection: close\r\n\r\n"
                ).encode("ascii", errors="strict")
                connection.sendall(request)
                response = http.client.HTTPResponse(connection)
                response.begin()
                content_type = response.headers.get("content-type", "")
                if response.status in {301, 302, 303, 307, 308}:
                    return FetchedPage(
                        status_code=response.status,
                        final_url=url,
                        content_type=content_type,
                        redirect_location=response.headers.get("location"),
                    )

                body = response.read(self.max_bytes + 1)
                if len(body) > self.max_bytes:
                    raise ValueError("Response exceeded the maximum allowed size")
                charset = response.headers.get_content_charset() or "utf-8"
                is_pdf = (
                    content_type.split(";", 1)[0].strip().lower() == "application/pdf"
                    or b"%PDF-" in body[:1024]
                )
                return FetchedPage(
                    status_code=response.status,
                    final_url=url,
                    content_type=content_type,
                    content=body.decode(
                        "latin-1" if is_pdf else charset,
                        errors="replace",
                    ),
                )
            except OSError as exc:
                last_error = exc
            finally:
                connection.close()
                if connection is not raw_socket:
                    raw_socket.close()

        raise OSError(f"Could not connect to the public website: {last_error}")


    def _discover_links(self, html: str, base_url: str) -> Sequence[str]:
        parser = _AnchorParser()
        try:
            parser.feed(html)
        except Exception:
            return []

        base_host = urlsplit(base_url).hostname
        if not base_host:
            return []
        base_origin = _origin_tuple(base_url)

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
            try:
                candidate_origin = _origin_tuple(absolute)
            except ValueError:
                continue
            if candidate_origin != base_origin:
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


def _origin_tuple(url: str) -> tuple[str, str, int]:
    parsed = urlsplit(url)
    default_port = 443 if parsed.scheme.lower() == "https" else 80
    return parsed.scheme.lower(), (parsed.hostname or "").lower(), parsed.port or default_port


def _page_contains_pdf(page: FetchedPage) -> bool:
    if (page.content_type or "").split(";", 1)[0].strip().lower() == "application/pdf":
        return True
    try:
        return b"%PDF-" in page.content.encode("latin-1")[:1024]
    except UnicodeEncodeError:
        return False
