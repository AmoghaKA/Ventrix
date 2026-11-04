import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple

from pydantic import BaseModel, Field

from app.financial.models import (
    EvidenceInput,
    ExtractionStatus,
    FinancialMetric,
    FinancialMetricKey,
    NormalizedFinancialValue,
    StatementType,
    UnresolvedFinancialFact,
)
from app.financial.normalizer import normalize_financial_value


@dataclass(frozen=True)
class _MetricSpec:
    key: FinancialMetricKey
    aliases: Tuple[str, ...]
    statement: StatementType


_SPECS = (
    _MetricSpec(FinancialMetricKey.CASH_AND_EQUIVALENTS, ("cash and cash equivalents", "cash equivalents", "cash balance"), StatementType.BALANCE_SHEET),
    _MetricSpec(FinancialMetricKey.SHAREHOLDERS_EQUITY, ("shareholders' equity", "shareholders’ equity", "stockholders' equity", "total equity"), StatementType.BALANCE_SHEET),
    _MetricSpec(FinancialMetricKey.CURRENT_LIABILITIES, ("current liabilities",), StatementType.BALANCE_SHEET),
    _MetricSpec(FinancialMetricKey.TOTAL_LIABILITIES, ("total liabilities", "liabilities"), StatementType.BALANCE_SHEET),
    _MetricSpec(FinancialMetricKey.CURRENT_ASSETS, ("current assets",), StatementType.BALANCE_SHEET),
    _MetricSpec(FinancialMetricKey.TOTAL_ASSETS, ("total assets", "assets"), StatementType.BALANCE_SHEET),
    _MetricSpec(FinancialMetricKey.SHORT_TERM_DEBT, ("short-term debt", "short term debt", "current debt"), StatementType.BALANCE_SHEET),
    _MetricSpec(FinancialMetricKey.LONG_TERM_DEBT, ("long-term debt", "long term debt", "non-current debt"), StatementType.BALANCE_SHEET),
    _MetricSpec(FinancialMetricKey.TOTAL_DEBT, ("total debt", "total borrowings"), StatementType.BALANCE_SHEET),
    _MetricSpec(FinancialMetricKey.OPERATING_CASH_FLOW, ("cash flow from operating activities", "operating cash flow", "net cash from operating activities"), StatementType.CASH_FLOW_STATEMENT),
    _MetricSpec(FinancialMetricKey.INVESTING_CASH_FLOW, ("cash flow from investing activities", "investing cash flow", "net cash from investing activities"), StatementType.CASH_FLOW_STATEMENT),
    _MetricSpec(FinancialMetricKey.FINANCING_CASH_FLOW, ("cash flow from financing activities", "financing cash flow", "net cash from financing activities"), StatementType.CASH_FLOW_STATEMENT),
    _MetricSpec(FinancialMetricKey.CAPITAL_EXPENDITURE, ("capital expenditures", "capital expenditure", "capex"), StatementType.CASH_FLOW_STATEMENT),
    _MetricSpec(FinancialMetricKey.FREE_CASH_FLOW, ("free cash flow",), StatementType.CASH_FLOW_STATEMENT),
    _MetricSpec(FinancialMetricKey.COST_OF_REVENUE, ("cost of revenue", "cost of sales", "cost of goods sold", "cogs"), StatementType.INCOME_STATEMENT),
    _MetricSpec(FinancialMetricKey.GROSS_PROFIT, ("gross profit",), StatementType.INCOME_STATEMENT),
    _MetricSpec(FinancialMetricKey.OPERATING_EXPENSES, ("operating expenses", "operating costs", "opex"), StatementType.INCOME_STATEMENT),
    _MetricSpec(FinancialMetricKey.OPERATING_INCOME, ("operating income", "income from operations", "operating profit"), StatementType.INCOME_STATEMENT),
    _MetricSpec(FinancialMetricKey.NET_INCOME, ("net income", "net profit", "profit after tax"), StatementType.INCOME_STATEMENT),
    _MetricSpec(FinancialMetricKey.NET_LOSS, ("net loss", "loss for the period", "loss for the year"), StatementType.INCOME_STATEMENT),
    _MetricSpec(FinancialMetricKey.EBITDA, ("ebitda",), StatementType.INCOME_STATEMENT),
    _MetricSpec(FinancialMetricKey.REVENUE, ("recognized revenue", "recognised revenue", "total revenue", "revenue", "net sales", "sales revenue", "turnover"), StatementType.INCOME_STATEMENT),
)

_ALIAS_LOOKUP = sorted(
    ((alias, spec) for spec in _SPECS for alias in spec.aliases),
    key=lambda item: len(item[0]),
    reverse=True,
)
_ALIAS_PATTERN = re.compile(
    r"(?<![\w])(?P<label>"
    + "|".join(re.escape(alias) for alias, _ in _ALIAS_LOOKUP)
    + r")(?![\w])",
    re.IGNORECASE,
)
_VALUE_PATTERN = re.compile(
    r"(?P<value>\(?\s*[+\-−]?\s*(?:(?-i:[A-Z]{3})|[$€£₹¥])?\s*"
    r"(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?\s*(?:thousands?|millions?|billions?|"
    r"lakhs?|lacs?|crores?|thousand|million|billion|lakh|lac|crore|cr|mn|bn|[kmb])?"
    r"\s*(?:%|percent|percentage)?\s*(?-i:[A-Z]{3})?\s*\)?)",
    re.IGNORECASE,
)
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|[\n;]+")
_PAGE_TAG = re.compile(r"\[Page\s+(\d+)\]", re.IGNORECASE)
_UNSUPPORTED_SCALE = re.compile(r"^(?:trillions?|quadrillions?|arab|kharab)\b", re.I)


class FinancialExtractionResult(BaseModel):
    metrics: List[FinancialMetric] = Field(default_factory=list)
    unresolved: List[UnresolvedFinancialFact] = Field(default_factory=list)
    missing_metrics: List[FinancialMetricKey] = Field(default_factory=list)


@dataclass
class _EvidenceContext:
    evidence: EvidenceInput
    text: str
    page_references: List[int] = field(default_factory=list)


def extract_financials(evidence_records: Iterable[Any]) -> FinancialExtractionResult:
    """Extract explicitly labelled facts from evidence records, without side effects."""
    result = FinancialExtractionResult()
    for record in evidence_records:
        evidence = EvidenceInput.model_validate(record)
        # Raw source text is preferred so summary text cannot be mistaken for a
        # separate claim. Fall back to the stored extraction summary if needed.
        text = evidence.raw_text.strip() or evidence.extracted_information.strip()
        if not text:
            continue
        context = _EvidenceContext(
            evidence=evidence,
            text=text,
            page_references=_page_references(evidence.source_metadata),
        )
        _extract_statement_metrics(context, result)
        _extract_funding(context, result)
    found_keys = {metric.metric_key for metric in result.metrics}
    found_keys.update(fact.metric_key for fact in result.unresolved if fact.metric_key is not None)
    result.missing_metrics = [key for key in FinancialMetricKey if key not in found_keys]
    return result


def _extract_statement_metrics(context: _EvidenceContext, result: FinancialExtractionResult) -> None:
    for sentence in _sentences(context.text):
        matches = list(_ALIAS_PATTERN.finditer(sentence))
        for index, label_match in enumerate(matches):
            spec = _spec_for(label_match.group("label"))
            if spec is None:
                continue
            end = matches[index + 1].start() if index + 1 < len(matches) else len(sentence)
            segment = sentence[label_match.end():end]
            values = [
                match for match in _VALUE_PATTERN.finditer(segment)
                if not _is_period_or_percentage(segment, match)
            ]
            excerpt = _clean_excerpt(sentence)
            pages = _pages_for_excerpt(context, excerpt)
            if not values:
                continue
            if any(_has_unsupported_scale(segment, value) for value in values):
                result.unresolved.append(_unresolved(context, spec.key, "the amount uses a scale that is not supported", excerpt, pages, ExtractionStatus.UNRESOLVED))
                continue
            if len(values) != 1:
                result.unresolved.append(_unresolved(context, spec.key, "multiple amounts are associated with this metric", excerpt, pages))
                continue
            parsed = normalize_financial_value(values[0].group("value"))
            if parsed is None:
                result.unresolved.append(_unresolved(context, spec.key, "the amount format is unsupported or ambiguous", excerpt, pages, ExtractionStatus.UNRESOLVED))
                continue
            result.metrics.append(_metric(
                context, spec, label_match.group("label"), parsed, excerpt, pages,
                _period(sentence), _actuality(sentence),
            ))


def _extract_funding(context: _EvidenceContext, result: FinancialExtractionResult) -> None:
    for sentence in _sentences(context.text):
        if not re.search(r"\b(raised|raising|funding|fundraise|fundraising|financing round|investment round)\b", sentence, re.I):
            continue
        excerpt = _clean_excerpt(sentence)
        pages = _pages_for_excerpt(context, excerpt)
        amount_match = re.search(
            r"\b(?:raised|secured|received|funding(?:\s+of)?|investment(?:\s+of)?)\s*(?:a\s+|an\s+)?(?:total(?:ling|ing)?\s*)?"
            r"(?P<amount>\(?\s*[+\-−]?\s*(?:(?-i:[A-Z]{3})|[$€£₹¥])?\s*"
            r"(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?\s*(?:thousands?|millions?|billions?|lakhs?|lacs?|crores?|"
            r"thousand|million|billion|lakh|lac|crore|cr|mn|bn|[kmb])?\s*(?-i:[A-Z]{3})?\s*\)?)",
            sentence,
            re.I,
        )
        if amount_match:
            parsed = normalize_financial_value(amount_match.group("amount"))
            if parsed and not _UNSUPPORTED_SCALE.match(sentence[amount_match.end():].lstrip()):
                spec = _MetricSpec(FinancialMetricKey.FUNDING_RAISED, ("funding raised",), StatementType.FUNDING)
                result.metrics.append(_metric(
                    context, spec, "funding raised", parsed, excerpt, pages,
                    _period(sentence), _actuality(sentence),
                ))
            else:
                result.unresolved.append(_unresolved(
                    context,
                    FinancialMetricKey.FUNDING_RAISED,
                    "the funding amount uses an unsupported currency or scale",
                    excerpt,
                    pages,
                    ExtractionStatus.UNRESOLVED,
                ))

        round_match = re.search(r"\b(pre[- ]?seed|seed|series\s+[A-Z]|series\s+[0-9]+|angel|bridge|venture debt|grant)\s+(?:funding\s+)?round\b", sentence, re.I)
        if round_match:
            _append_text_metric(context, result, FinancialMetricKey.FUNDING_ROUND, "funding round", round_match.group(0), excerpt, pages, _period(sentence))
            _append_text_metric(context, result, FinancialMetricKey.FUNDING_STAGE, "funding stage", round_match.group(1), excerpt, pages, _period(sentence))
        elif re.search(r"\b(pre[- ]?seed|seed|series\s+[A-Z]|series\s+[0-9]+|angel|bridge)\b", sentence, re.I):
            stage = re.search(r"\b(pre[- ]?seed|seed|series\s+[A-Z]|series\s+[0-9]+|angel|bridge)\b", sentence, re.I)
            if stage:
                _append_text_metric(context, result, FinancialMetricKey.FUNDING_STAGE, "funding stage", stage.group(1), excerpt, pages, _period(sentence))

        date_match = re.search(
            r"\b(?:on\s+)?(?P<date>\d{4}-\d{2}-\d{2}|(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2},?\s+\d{4})\b",
            sentence,
            re.I,
        )
        if date_match:
            parsed_date = _parse_date(date_match.group("date"))
            if parsed_date:
                result.metrics.append(_funding_date_metric(context, excerpt, pages, parsed_date=parsed_date))
        else:
            partial_date = re.search(
                r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
                r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|"
                r"Dec(?:ember)?)\s+\d{4}\b",
                sentence,
                re.I,
            )
            if partial_date:
                result.metrics.append(_funding_date_metric(
                    context, excerpt, pages, date_text=partial_date.group(0)
                ))
        investors = re.search(r"\b(?:led by|investors? (?:include|included|were)|backed by|from)\s+(?P<names>[A-Z][\w&.,'’ -]{1,100})", sentence)
        if investors:
            names = re.split(r"\s+(?:and|alongside)\s+|,\s*", investors.group("names"), maxsplit=3)[0:4]
            names = [name.strip(" .") for name in names if name.strip(" .")]
            if names:
                _append_text_metric(context, result, FinancialMetricKey.NAMED_INVESTORS, "named investors", ", ".join(names), excerpt, pages, _period(sentence))


def _metric(context: _EvidenceContext, spec: _MetricSpec, label: str,
            parsed: NormalizedFinancialValue, excerpt: str, pages: List[int],
            period: Dict[str, Any], actuality: Optional[str]) -> FinancialMetric:
    return FinancialMetric(
        metric_key=spec.key,
        original_metric_label=label,
        normalized_value=parsed.normalized_value,
        original_numeric_value=parsed.original_numeric_value,
        currency_code=parsed.currency_code,
        currency_symbol=parsed.currency_symbol,
        original_unit_scale=parsed.original_unit_scale,
        normalized_unit=parsed.normalized_unit,
        statement_type=spec.statement,
        source_evidence_id=context.evidence.id,
        source_url=context.evidence.source_url,
        source_title=context.evidence.source_title,
        source_category=context.evidence.source_category,
        source_publication_date=context.evidence.publication_date,
        source_retrieval_date=context.evidence.retrieval_date,
        supporting_excerpt=excerpt,
        pdf_page_references=pages,
        evidence_verification_status=context.evidence.verification_status,
        actuality=actuality,
        **period,
    )


def _append_text_metric(context: _EvidenceContext, result: FinancialExtractionResult,
                        key: FinancialMetricKey, label: str, value: str,
                        excerpt: str, pages: List[int], period: Dict[str, Any]) -> None:
    result.metrics.append(FinancialMetric(
        metric_key=key,
        original_metric_label=label,
        text_value=value,
        statement_type=StatementType.FUNDING,
        source_evidence_id=context.evidence.id,
        source_url=context.evidence.source_url,
        source_title=context.evidence.source_title,
        source_category=context.evidence.source_category,
        source_publication_date=context.evidence.publication_date,
        source_retrieval_date=context.evidence.retrieval_date,
        supporting_excerpt=excerpt,
        pdf_page_references=pages,
        evidence_verification_status=context.evidence.verification_status,
        actuality=_actuality(excerpt),
        **period,
    ))


def _funding_date_metric(
    context: _EvidenceContext,
    excerpt: str,
    pages: List[int],
    *,
    parsed_date: Optional[date] = None,
    date_text: Optional[str] = None,
) -> FinancialMetric:
    return FinancialMetric(
        metric_key=FinancialMetricKey.FUNDING_DATE,
        original_metric_label="funding date",
        date_value=parsed_date,
        text_value=date_text,
        reporting_period_label=parsed_date.isoformat() if parsed_date else date_text,
        statement_type=StatementType.FUNDING,
        source_evidence_id=context.evidence.id,
        source_url=context.evidence.source_url,
        source_title=context.evidence.source_title,
        source_category=context.evidence.source_category,
        source_publication_date=context.evidence.publication_date,
        source_retrieval_date=context.evidence.retrieval_date,
        supporting_excerpt=excerpt,
        pdf_page_references=pages,
        evidence_verification_status=context.evidence.verification_status,
        actuality=_actuality(excerpt),
    )


def _spec_for(label: str) -> Optional[_MetricSpec]:
    lowered = label.lower()
    return next((spec for alias, spec in _ALIAS_LOOKUP if alias.lower() == lowered), None)


def _sentences(text: str) -> List[str]:
    return [_clean_excerpt(item) for item in _SENTENCE_SPLIT.split(text) if _clean_excerpt(item)]


def _clean_excerpt(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()[:1200]


def _period(sentence: str) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    year: Optional[int] = None
    quarter_match = re.search(r"\bQ([1-4])\s*(?:FY\s*)?((?:19|20)\d{2})\b|\bFY\s*((?:19|20)\d{2})\s*Q([1-4])\b", sentence, re.I)
    if quarter_match:
        if quarter_match.group(2):
            result["fiscal_quarter"] = int(quarter_match.group(1))
            year = int(quarter_match.group(2))
        else:
            year = int(quarter_match.group(3))
            result["fiscal_quarter"] = int(quarter_match.group(4))
    fy = re.search(r"\b(?:FY|fiscal\s+year)\s*((?:19|20)\d{2})(?:\s*[-/]\s*((?:19|20)?\d{2}))?\b", sentence, re.I)
    if fy:
        year = int(fy.group(1))
        result["reporting_period_label"] = fy.group(0)
    elif year is None:
        calendar = re.search(
            r"\b(?:CY\s*|calendar year\s+|in\s+|for\s+|during\s+)"
            r"((?:19|20)\d{2})\b|\b((?:19|20)\d{2})\s+(?:actual\s+|forecast\s+)?(?:revenue|income|sales)\b",
            sentence,
            re.I,
        )
        if calendar:
            year = int(calendar.group(1) or calendar.group(2))
            result["reporting_period_label"] = str(year)
    elif "fiscal_quarter" in result:
        result["reporting_period_label"] = f"Q{result['fiscal_quarter']} FY{year}"
    if year:
        result["fiscal_year"] = year
    date_pattern = (
        r"(?:\d{4}-\d{2}-\d{2}|(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|"
        r"May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|"
        r"Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2},?\s+\d{4})"
    )
    date_range = re.search(
        rf"\b(?:from|between)\s+(?P<start>{date_pattern})\s+(?:to|and)\s+(?P<end>{date_pattern})\b",
        sentence,
        re.I,
    )
    if date_range:
        start_date = _parse_date(date_range.group("start"))
        end_date = _parse_date(date_range.group("end"))
        if start_date and end_date:
            result["period_start_date"] = start_date
            result["period_end_date"] = end_date
    ended = re.search(
        r"\b(?:year|quarter|period)\s+ended\s+(?P<date>\d{4}-\d{2}-\d{2}|"
        r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
        r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|"
        r"Dec(?:ember)?)\s+\d{1,2},?\s+\d{4})",
        sentence,
        re.I,
    )
    if ended:
        end_date = _parse_date(ended.group("date"))
        if end_date:
            result["period_end_date"] = end_date
            if year is None:
                result["fiscal_year"] = end_date.year
    return result


def _actuality(sentence: str) -> Optional[str]:
    if re.search(r"\b(forecast|projected|projection|target|expected|budgeted|plan(?:ned)?)\b", sentence, re.I):
        return "forecast_or_target"
    if re.search(r"\b(actual|reported|recorded|for the year ended|year ended|historical)\b", sentence, re.I):
        return "actual"
    return None


def _parse_date(value: str) -> Optional[date]:
    for pattern in ("%Y-%m-%d", "%B %d, %Y", "%B %d %Y", "%b %d, %Y", "%b %d %Y"):
        try:
            return datetime.strptime(value, pattern).date()
        except ValueError:
            continue
    return None


def _page_references(metadata: Dict[str, Any]) -> List[int]:
    value = metadata.get("page_references", []) if isinstance(metadata, dict) else []
    if not isinstance(value, (list, tuple)):
        return []
    return sorted({page for page in value if isinstance(page, int) and page > 0})


def _pages_for_excerpt(context: _EvidenceContext, excerpt: str) -> List[int]:
    excerpt_tag = _PAGE_TAG.search(excerpt)
    if excerpt_tag:
        return [int(excerpt_tag.group(1))]
    position = context.text.find(excerpt)
    if position >= 0:
        preceding = list(_PAGE_TAG.finditer(context.text, 0, position + 1))
        if preceding:
            return [int(preceding[-1].group(1))]
    return context.page_references


def _is_period_or_percentage(segment: str, match: re.Match) -> bool:
    value = match.group("value").strip()
    # Percent changes are not monetary statement values. Bare years and
    # quarter numbers describe periods rather than amounts.
    if re.search(r"(?:%|percent|percentage)\s*\)?$", value, re.I):
        return True
    date_spans = re.finditer(
        r"\b\d{4}-\d{2}-\d{2}\b|\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
        r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+"
        r"\d{1,2},?\s+\d{4}\b",
        segment,
        re.I,
    )
    if any(span.start() <= match.start() and match.end() <= span.end() for span in date_spans):
        return True
    bare = re.fullmatch(r"\(?\s*(\d{1,4})\s*\)?", value)
    if not bare:
        return False
    number = int(bare.group(1))
    if 1900 <= number <= 2099:
        return True
    before = segment[max(0, match.start() - 5):match.start()]
    after = segment[match.end():match.end() + 8]
    return bool(re.search(r"Q\s*$", before, re.I) or re.match(r"\s*FY\b", after, re.I))


def _has_unsupported_scale(segment: str, match: re.Match) -> bool:
    return _UNSUPPORTED_SCALE.match(segment[match.end():].lstrip()) is not None


def _unresolved(context: _EvidenceContext, key: FinancialMetricKey, reason: str,
                excerpt: str, pages: List[int],
                status: ExtractionStatus = ExtractionStatus.AMBIGUOUS) -> UnresolvedFinancialFact:
    return UnresolvedFinancialFact(
        metric_key=key,
        reason=reason,
        supporting_excerpt=excerpt,
        source_evidence_id=context.evidence.id,
        source_url=context.evidence.source_url,
        source_title=context.evidence.source_title,
        evidence_verification_status=context.evidence.verification_status,
        pdf_page_references=pages,
        extraction_status=status,
    )
