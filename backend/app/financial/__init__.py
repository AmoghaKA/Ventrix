"""Deterministic financial fact extraction from stored evidence."""

from app.financial.extractor import FinancialExtractionResult, extract_financials
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

__all__ = [
    "EvidenceInput",
    "ExtractionStatus",
    "FinancialExtractionResult",
    "FinancialMetric",
    "FinancialMetricKey",
    "NormalizedFinancialValue",
    "StatementType",
    "UnresolvedFinancialFact",
    "extract_financials",
    "normalize_financial_value",
]
