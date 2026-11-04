from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class FinancialMetricKey(str, Enum):
    REVENUE = "revenue"
    COST_OF_REVENUE = "cost_of_revenue"
    GROSS_PROFIT = "gross_profit"
    OPERATING_EXPENSES = "operating_expenses"
    OPERATING_INCOME = "operating_income"
    EBITDA = "ebitda"
    NET_INCOME = "net_income"
    NET_LOSS = "net_loss"
    CASH_AND_EQUIVALENTS = "cash_and_cash_equivalents"
    CURRENT_ASSETS = "current_assets"
    TOTAL_ASSETS = "total_assets"
    CURRENT_LIABILITIES = "current_liabilities"
    TOTAL_LIABILITIES = "total_liabilities"
    SHORT_TERM_DEBT = "short_term_debt"
    LONG_TERM_DEBT = "long_term_debt"
    TOTAL_DEBT = "total_debt"
    SHAREHOLDERS_EQUITY = "shareholders_equity"
    OPERATING_CASH_FLOW = "operating_cash_flow"
    INVESTING_CASH_FLOW = "investing_cash_flow"
    FINANCING_CASH_FLOW = "financing_cash_flow"
    CAPITAL_EXPENDITURE = "capital_expenditure"
    FREE_CASH_FLOW = "free_cash_flow"
    FUNDING_RAISED = "funding_raised"
    FUNDING_ROUND = "funding_round"
    FUNDING_DATE = "funding_date"
    FUNDING_STAGE = "funding_stage"
    NAMED_INVESTORS = "named_investors"


class StatementType(str, Enum):
    INCOME_STATEMENT = "income_statement"
    BALANCE_SHEET = "balance_sheet"
    CASH_FLOW_STATEMENT = "cash_flow_statement"
    FUNDING = "funding"
    UNSPECIFIED = "unspecified"


class ExtractionStatus(str, Enum):
    EXTRACTED = "extracted"
    AMBIGUOUS = "ambiguous"
    UNRESOLVED = "unresolved"


class EvidenceInput(BaseModel):
    """Read-only adapter for ORM Evidence objects or compatible mappings."""

    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: int = Field(gt=0)
    source_url: str = Field(min_length=1, max_length=2048)
    source_title: str = ""
    source_category: str = ""
    extracted_information: str = ""
    raw_text: str = ""
    publication_date: Optional[datetime] = None
    retrieval_date: Optional[datetime] = None
    verification_status: str = "unverified"
    source_metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("source_url")
    @classmethod
    def trim_source_url(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("source_url cannot be blank")
        return value


class FinancialMetric(BaseModel):
    metric_key: FinancialMetricKey
    original_metric_label: str = Field(min_length=1)
    normalized_value: Optional[Decimal] = None
    original_numeric_value: Optional[str] = None
    text_value: Optional[str] = None
    date_value: Optional[date] = None
    currency_code: Optional[str] = None
    currency_symbol: Optional[str] = None
    original_unit_scale: Optional[str] = None
    normalized_unit: Optional[str] = None
    reporting_period_label: Optional[str] = None
    period_start_date: Optional[date] = None
    period_end_date: Optional[date] = None
    fiscal_year: Optional[int] = None
    fiscal_quarter: Optional[int] = Field(default=None, ge=1, le=4)
    statement_type: StatementType = StatementType.UNSPECIFIED
    source_evidence_id: int = Field(gt=0)
    source_url: str
    source_title: str = ""
    source_category: str = ""
    source_publication_date: Optional[datetime] = None
    source_retrieval_date: Optional[datetime] = None
    supporting_excerpt: str = Field(min_length=1)
    pdf_page_references: List[int] = Field(default_factory=list)
    evidence_verification_status: str
    extraction_method: str = "deterministic_label_match"
    extraction_status: ExtractionStatus = ExtractionStatus.EXTRACTED
    actuality: Optional[str] = None

    @field_validator("currency_code")
    @classmethod
    def validate_currency_code(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.upper()
        if len(value) != 3 or not value.isalpha():
            raise ValueError("currency_code must be a three-letter ISO-style code")
        return value

    @field_validator("pdf_page_references")
    @classmethod
    def validate_pages(cls, value: List[int]) -> List[int]:
        if any(page < 1 for page in value):
            raise ValueError("PDF page references must be positive")
        return sorted(set(value))

    @model_validator(mode="after")
    def validate_supporting_data(self):
        if self.normalized_value is not None and not self.original_numeric_value:
            raise ValueError("numeric values must retain their original representation")
        if self.metric_key == FinancialMetricKey.FUNDING_DATE:
            if self.date_value is None and not self.text_value:
                raise ValueError("funding dates require an explicit date value")
        elif self.metric_key in {
            FinancialMetricKey.FUNDING_ROUND,
            FinancialMetricKey.FUNDING_STAGE,
            FinancialMetricKey.NAMED_INVESTORS,
        } and not self.text_value:
            raise ValueError("text funding facts require a value")
        return self


class UnresolvedFinancialFact(BaseModel):
    metric_key: Optional[FinancialMetricKey] = None
    reason: str
    supporting_excerpt: str = Field(min_length=1)
    source_evidence_id: int = Field(gt=0)
    source_url: str
    source_title: str = ""
    evidence_verification_status: str = "unverified"
    pdf_page_references: List[int] = Field(default_factory=list)
    extraction_status: ExtractionStatus = ExtractionStatus.AMBIGUOUS


class NormalizedFinancialValue(BaseModel):
    normalized_value: Decimal
    original_numeric_value: str
    currency_code: Optional[str] = None
    currency_symbol: Optional[str] = None
    original_unit_scale: Optional[str] = None
    normalized_unit: str


class CalculationKey(str, Enum):
    GROSS_PROFIT_MARGIN = "gross_profit_margin"
    OPERATING_PROFIT_MARGIN = "operating_profit_margin"
    NET_PROFIT_MARGIN = "net_profit_margin"
    EBITDA_MARGIN = "ebitda_margin"
    CURRENT_RATIO = "current_ratio"
    CASH_RATIO = "cash_ratio"
    NET_WORKING_CAPITAL = "net_working_capital"
    DEBT_TO_EQUITY_RATIO = "debt_to_equity_ratio"
    LIABILITIES_TO_ASSETS_RATIO = "liabilities_to_assets_ratio"
    OPERATING_CASH_FLOW_MARGIN = "operating_cash_flow_margin"
    FREE_CASH_FLOW_MARGIN = "free_cash_flow_margin"
    FREE_CASH_FLOW = "free_cash_flow"
    ANNUAL_REVENUE_GROWTH = "annual_revenue_growth"


class CalculationStatus(str, Enum):
    CALCULATED = "calculated"
    UNAVAILABLE = "unavailable"
    AMBIGUOUS = "ambiguous"


class CalculationUnit(str, Enum):
    PERCENTAGE = "percentage"
    RATIO = "ratio"
    CURRENCY_AMOUNT = "currency_amount"


class CalculationInput(BaseModel):
    metric_key: FinancialMetricKey
    original_metric_label: str
    original_value: Optional[str] = None
    normalized_value: Optional[Decimal] = None
    currency_code: Optional[str] = None
    currency_symbol: Optional[str] = None
    original_unit_scale: Optional[str] = None
    normalized_unit: Optional[str] = None
    reporting_period_label: Optional[str] = None
    period_start_date: Optional[date] = None
    period_end_date: Optional[date] = None
    fiscal_year: Optional[int] = None
    fiscal_quarter: Optional[int] = None
    actuality: Optional[str] = None
    source_evidence_id: int = Field(gt=0)
    source_url: str
    source_title: str = ""
    supporting_excerpt: str
    evidence_verification_status: str
    extraction_status: ExtractionStatus = ExtractionStatus.EXTRACTED


class FinancialCalculation(BaseModel):
    calculation_key: CalculationKey
    calculation_name: str
    value: Optional[Decimal] = None
    unit: CalculationUnit
    formula: str
    input_metrics: List[CalculationInput] = Field(default_factory=list)
    reporting_period_label: Optional[str] = None
    period_start_date: Optional[date] = None
    period_end_date: Optional[date] = None
    fiscal_year: Optional[int] = None
    fiscal_quarter: Optional[int] = None
    actuality: Optional[str] = None
    currency_code: Optional[str] = None
    currency_symbol: Optional[str] = None
    source_evidence_ids: List[int] = Field(default_factory=list)
    source_urls: List[str] = Field(default_factory=list)
    supporting_excerpts: List[str] = Field(default_factory=list)
    evidence_verification_status: str = "unavailable"
    status: CalculationStatus
    explanation: Optional[str] = None
    rounding: str = "ROUND_HALF_UP; percentages to 2 decimals, ratios to 4 decimals"


class FinancialCalculationResult(BaseModel):
    calculated: List[FinancialCalculation] = Field(default_factory=list)
    unavailable: List[FinancialCalculation] = Field(default_factory=list)
    ambiguous: List[FinancialCalculation] = Field(default_factory=list)
