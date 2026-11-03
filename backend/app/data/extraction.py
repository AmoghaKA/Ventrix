import hashlib
import io
import os.path
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Dict, List, Optional, Union
from urllib.parse import urlsplit

from app.data.retrieval import RetrievedSource

_CATEGORY_AGENTS = {
    "company": "company_research_agent",
    "financial": "financial_analysis_agent",
    "marketing": "market_analysis_agent",
    "legal": "legal_compliance_agent",
}

_CATEGORY_TERMS = {
    "legal": (
        "privacy",
        "terms",
        "legal",
        "policy",
        "compliance",
        "gdpr",
        "cookie",
        "licence",
        "license",
    ),
    "financial": (
        "pricing",
        "investor",
        "funding",
        "financial",
        "revenue",
        "valuation",
        "series",
        "raise",
    ),
    "marketing": (
        "customer",
        "case-study",
        "case study",
        "testimonial",
        "product",
        "solution",
        "news",
        "press",
        "blog",
        "media",
    ),
}

_BLOCK_TAGS = {
    "article",
    "blockquote",
    "br",
    "dd",
    "div",
    "dl",
    "dt",
    "figcaption",
    "figure",
    "footer",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "header",
    "hr",
    "li",
    "main",
    "nav",
    "ol",
    "p",
    "pre",
    "section",
    "table",
    "td",
    "th",
    "tr",
    "ul",
}

_SKIP_TAGS = {"noscript", "script", "style", "svg", "template"}

_DATE_META_KEYS = (
    "article:published_time",
    "datepublished",
    "date",
    "pubdate",
    "publication_date",
    "publish_date",
)

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


@dataclass(frozen=True)
class ExtractedEvidence:
    url: str
    source_title: str
    source_category: str
    extracted_information: str
    raw_text: str
    publication_date: Optional[datetime]
    related_agent: str
    findings: List[Dict[str, str]]
    source_metadata: Dict[str, object]
    content_hash: str


@dataclass(frozen=True)
class ExtractionFailure:
    """A safe, structured record explaining why a source was not evidence."""

    source_url: str
    failure_stage: str
    error_category: str
    description: str
    document_name: Optional[str] = None


ExtractionResult = Union[ExtractedEvidence, ExtractionFailure]


class _DocumentParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_parts: List[str] = []
        self.text_parts: List[str] = []
        self.meta: Dict[str, str] = {}
        self.time_value: Optional[str] = None
        self._skip_depth = 0
        self._in_title = False

    def handle_starttag(self, tag: str, attrs) -> None:
        tag = tag.lower()
        attributes = {name.lower(): (value or "") for name, value in attrs}

        if tag in _SKIP_TAGS:
            self._skip_depth += 1
            return
        if tag == "title":
            self._in_title = True
        elif tag == "meta":
            key = (
                attributes.get("property")
                or attributes.get("name")
                or attributes.get("itemprop")
            ).strip().lower()
            content = attributes.get("content", "").strip()
            if key and content:
                self.meta.setdefault(key, content)
        elif tag == "time" and self.time_value is None:
            value = attributes.get("datetime", "").strip()
            if value:
                self.time_value = value

        if tag in _BLOCK_TAGS:
            self.text_parts.append("\n")

    def handle_startendtag(self, tag: str, attrs) -> None:
        if tag.lower() in {"br", "hr"}:
            self.text_parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in _SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if tag == "title":
            self._in_title = False
        if tag in _BLOCK_TAGS:
            self.text_parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if self._in_title:
            self.title_parts.append(data)
            return
        self.text_parts.append(data)


def extract_source_detailed(
    source: RetrievedSource,
    *,
    max_document_bytes: int = 2_000_000,
    max_pdf_pages: int = 100,
    max_extracted_characters: int = 200_000,
) -> ExtractionResult:
    """Extract a supported source or return a structured safe failure.

    PDFs are size limited before parsing and page/text limited during parsing.
    No password guessing or OCR is attempted.
    """
    if _is_pdf(source):
        return _extract_pdf_source(
            source,
            max_document_bytes=max_document_bytes,
            max_pdf_pages=max_pdf_pages,
            max_extracted_characters=max_extracted_characters,
        )
    if len(source.content.encode("utf-8", errors="replace")) > max_document_bytes:
        return ExtractionFailure(
            source_url=source.final_url or source.url,
            failure_stage="extraction",
            error_category="document_too_large",
            description="The document exceeds the configured extraction size limit.",
        )
    return _extract_html_source(source)


def extract_source(source: RetrievedSource) -> Optional[ExtractedEvidence]:
    """Compatibility wrapper returning evidence or ``None`` for old callers."""
    result = extract_source_detailed(source)
    return result if isinstance(result, ExtractedEvidence) else None


def _is_pdf(source: RetrievedSource) -> bool:
    content_type = (source.content_type or "").split(";", 1)[0].strip().lower()
    if content_type == "application/pdf":
        return True
    try:
        prefix = source.content.encode("latin-1")[:1024]
    except UnicodeEncodeError:
        return False
    return b"%PDF-" in prefix


def _extract_pdf_source(
    source: RetrievedSource,
    *,
    max_document_bytes: int,
    max_pdf_pages: int,
    max_extracted_characters: int,
) -> ExtractionResult:
    try:
        pdf_bytes = source.content.encode("latin-1")
    except UnicodeEncodeError:
        return ExtractionFailure(
            source_url=source.final_url or source.url,
            failure_stage="document_decode",
            error_category="unsupported_encoding",
            description="The PDF response could not be represented as document bytes.",
        )

    document_name = os.path.basename(urlsplit(source.final_url or source.url).path)
    document_name = document_name or "PDF document"
    if len(pdf_bytes) > max_document_bytes:
        return ExtractionFailure(
            source_url=source.final_url or source.url,
            failure_stage="document_validation",
            error_category="document_too_large",
            description="The PDF exceeds the configured extraction size limit.",
            document_name=document_name,
        )
    if b"%PDF-" not in pdf_bytes[:1024]:
        return ExtractionFailure(
            source_url=source.final_url or source.url,
            failure_stage="document_validation",
            error_category="malformed_pdf",
            description="The response is labelled as a PDF but has no valid PDF header.",
            document_name=document_name,
        )

    try:
        from pypdf import PdfReader
    except ImportError:
        return ExtractionFailure(
            source_url=source.final_url or source.url,
            failure_stage="parser_setup",
            error_category="parser_unavailable",
            description="The PDF parser is not installed in this environment.",
            document_name=document_name,
        )

    try:
        reader = PdfReader(io.BytesIO(pdf_bytes), strict=False)
        if reader.is_encrypted:
            return ExtractionFailure(
                source_url=source.final_url or source.url,
                failure_stage="document_open",
                error_category="encrypted_pdf",
                description="The PDF is encrypted and no password was supplied.",
                document_name=document_name,
            )
        page_count = len(reader.pages)
        if page_count > max_pdf_pages:
            return ExtractionFailure(
                source_url=source.final_url or source.url,
                failure_stage="document_validation",
                error_category="page_limit_exceeded",
                description="The PDF exceeds the configured page processing limit.",
                document_name=document_name,
            )

        page_texts: List[str] = []
        page_references: List[int] = []
        extracted_size = 0
        for page_number, page in enumerate(reader.pages, start=1):
            page_text = _collapse_whitespace(page.extract_text() or "")
            if not page_text:
                continue
            extracted_size += len(page_text)
            if extracted_size > max_extracted_characters:
                return ExtractionFailure(
                    source_url=source.final_url or source.url,
                    failure_stage="text_extraction",
                    error_category="text_limit_exceeded",
                    description="The PDF text exceeds the configured extraction limit.",
                    document_name=document_name,
                )
            page_texts.append(f"[Page {page_number}] {page_text}")
            page_references.append(page_number)

        if not page_texts:
            return ExtractionFailure(
                source_url=source.final_url or source.url,
                failure_stage="text_extraction",
                error_category="empty_pdf",
                description="The PDF contains no extractable text.",
                document_name=document_name,
            )

        metadata = reader.metadata
        metadata_title = _collapse_whitespace(str(metadata.title or "")) if metadata else ""
        title = metadata_title or document_name
        raw_text = "\n".join(page_texts)
        excerpt = _excerpt(raw_text, "")
        if len(raw_text) < 80 or not excerpt:
            return ExtractionFailure(
                source_url=source.final_url or source.url,
                failure_stage="text_validation",
                error_category="insufficient_text",
                description="The PDF text is too short to create usable evidence.",
                document_name=title,
            )

        category = _categorise(source.final_url, title, "", raw_text)
        information = _build_extracted_information(title, "", excerpt)
        source_metadata: Dict[str, object] = {
            "final_url": source.final_url,
            "content_type": source.content_type,
            "from_cache": source.from_cache,
            "document_type": "pdf",
            "document_name": document_name,
            "page_count": page_count,
            "page_references": page_references,
            "extraction_method": "pypdf_text",
            "word_count": len(raw_text.split()),
        }
        if metadata and metadata.author:
            source_metadata["document_author"] = str(metadata.author)[:512]
        if metadata and metadata.creation_date:
            source_metadata["document_creation_date"] = str(metadata.creation_date)[:64]
        if metadata and metadata.subject:
            source_metadata["document_subject"] = str(metadata.subject)[:512]

        return ExtractedEvidence(
            url=source.final_url,
            source_title=title[:512],
            source_category=category,
            extracted_information=information,
            raw_text=raw_text[:20_000],
            publication_date=None,
            related_agent=_CATEGORY_AGENTS[category],
            findings=[
                {
                    "type": "excerpt",
                    "value": excerpt,
                    "pages": ",".join(map(str, page_references)),
                }
            ],
            source_metadata=source_metadata,
            content_hash=hashlib.sha256(pdf_bytes).hexdigest(),
        )
    except Exception:
        return ExtractionFailure(
            source_url=source.final_url or source.url,
            failure_stage="text_extraction",
            error_category="malformed_pdf",
            description="The PDF could not be parsed or its text could not be extracted.",
            document_name=document_name,
        )


def _extract_html_source(
    source: RetrievedSource,
) -> Union[ExtractedEvidence, ExtractionFailure]:
    parser = _DocumentParser()
    try:
        parser.feed(source.content)
        parser.close()
    except Exception:
        return ExtractionFailure(
            source_url=source.final_url or source.url,
            failure_stage="html_parse",
            error_category="malformed_html",
            description="The HTML source could not be parsed into readable content.",
        )

    title = (
        parser.meta.get("og:title")
        or parser.meta.get("twitter:title")
        or " ".join(parser.title_parts)
    )
    title = _collapse_whitespace(title)
    description = _collapse_whitespace(
        parser.meta.get("og:description")
        or parser.meta.get("twitter:description")
        or parser.meta.get("description")
        or ""
    )

    raw_text = _visible_text(parser.text_parts)
    publication_date = _publication_date(parser.meta, parser.time_value)

    excerpt = _excerpt(raw_text, description)
    if not description and not excerpt and len(raw_text) < 120:
        return ExtractionFailure(
            source_url=source.final_url or source.url,
            failure_stage="text_validation",
            error_category="insufficient_text",
            description="The source contains too little readable text to create evidence.",
        )

    extracted_information = _build_extracted_information(
        title,
        description,
        excerpt,
    )
    if not extracted_information:
        return ExtractionFailure(
            source_url=source.final_url or source.url,
            failure_stage="text_validation",
            error_category="empty_content",
            description="The source did not contain extractable evidence text.",
        )

    source_title = title or _fallback_title(source.final_url)
    category = _categorise(source.final_url, title, description, raw_text)
    findings = _findings(title, description, excerpt)

    metadata: Dict[str, object] = {
        "final_url": source.final_url,
        "content_type": source.content_type,
        "from_cache": source.from_cache,
        "word_count": len(raw_text.split()),
        "extraction_method": "deterministic_html",
    }
    if description:
        metadata["description"] = description

    return ExtractedEvidence(
        url=source.final_url,
        source_title=source_title[:512],
        source_category=category,
        extracted_information=extracted_information,
        raw_text=raw_text[:20_000],
        publication_date=publication_date,
        related_agent=_CATEGORY_AGENTS[category],
        findings=findings,
        source_metadata=metadata,
        content_hash=hashlib.sha256(
            source.content.encode("utf-8")
        ).hexdigest(),
    )


def _visible_text(parts: List[str]) -> str:
    text = "".join(parts)
    lines = [_collapse_whitespace(line) for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def _collapse_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _excerpt(raw_text: str, description: str) -> str:
    candidates = [
        sentence.strip()
        for sentence in _SENTENCE_SPLIT.split(raw_text)
        if 40 <= len(sentence.strip()) <= 500
    ]

    if description:
        candidates = [
            sentence
            for sentence in candidates
            if sentence.lower() != description.lower()
        ]

    selected: List[str] = []
    for candidate in candidates:
        if candidate in selected:
            continue
        selected.append(candidate)
        if len(selected) == 3:
            break

    excerpt = " ".join(selected)
    if excerpt:
        return excerpt

    if len(raw_text) >= 80:
        return raw_text[:600].rsplit(" ", 1)[0].strip()
    return ""


def _build_extracted_information(
    title: str,
    description: str,
    excerpt: str,
) -> str:
    parts: List[str] = []
    if title:
        parts.append(f"Title: {title}")
    if description:
        parts.append(f"Description: {description}")
    if excerpt and excerpt != description:
        parts.append(f"Excerpt: {excerpt}")
    return "\n".join(parts)


def _findings(
    title: str,
    description: str,
    excerpt: str,
) -> List[Dict[str, str]]:
    findings: List[Dict[str, str]] = []
    if title:
        findings.append({"type": "title", "value": title})
    if description:
        findings.append({"type": "description", "value": description})
    if excerpt and excerpt != description:
        findings.append({"type": "excerpt", "value": excerpt})
    return findings


def _fallback_title(url: str) -> str:
    parsed = urlsplit(url)
    path = parsed.path.strip("/")
    return path.replace("-", " ").replace("_", " ") or parsed.hostname or url


def _categorise(
    url: str,
    title: str,
    description: str,
    raw_text: str,
) -> str:
    parsed = urlsplit(url)
    hint = f"{parsed.path} {parsed.query} {title} {description}".lower()

    for category in ("legal", "financial", "marketing"):
        if any(term in hint for term in _CATEGORY_TERMS[category]):
            return category

    body_hint = raw_text[:600].lower()
    for category in ("legal", "financial", "marketing"):
        if any(term in body_hint for term in _CATEGORY_TERMS[category]):
            return category

    return "company"


def _publication_date(
    meta: Dict[str, str],
    time_value: Optional[str],
) -> Optional[datetime]:
    for key in _DATE_META_KEYS:
        value = meta.get(key)
        if value:
            parsed = _parse_date(value)
            if parsed:
                return parsed

    if time_value:
        return _parse_date(time_value)
    return None


def _parse_date(value: str) -> Optional[datetime]:
    candidate = value.strip()
    if not candidate:
        return None

    try:
        parsed = datetime.fromisoformat(candidate.replace("Z", "+00:00"))
    except ValueError:
        parsed = None

    if parsed is None:
        for fmt in (
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%d %B %Y",
            "%B %d, %Y",
            "%d %b %Y",
            "%b %d, %Y",
        ):
            try:
                parsed = datetime.strptime(candidate, fmt)
                break
            except ValueError:
                continue

    if parsed is None:
        return None

    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed
