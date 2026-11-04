"""Deterministic, period-aware calculations over extracted financial metrics."""

import re
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP, localcontext
from typing import Iterable, List, Optional, Sequence, Tuple

from app.financial.models import (
    CalculationInput,
    CalculationKey,
    CalculationStatus,
    CalculationUnit,
    FinancialCalculation,
    FinancialCalculationResult,
    FinancialMetric,
    FinancialMetricKey,
)


_PERCENT_QUANTUM = Decimal("0.01")
_RATIO_QUANTUM = Decimal("0.0001")


@dataclass
class _Selection:
    records: List[FinancialMetric]
    record: Optional[FinancialMetric] = None
    problem: Optional[str] = None
    ambiguous: bool = False


@dataclass(frozen=True)
class _CalculationSpec:
    key: CalculationKey
    name: str
    formula: str
    unit: CalculationUnit
    first_input: FinancialMetricKey
    second_input: FinancialMetricKey
    operation: str


_PAIR_SPECS = (
    _CalculationSpec(CalculationKey.GROSS_PROFIT_MARGIN, "Gross profit margin", "(Gross Profit / Revenue) × 100", CalculationUnit.PERCENTAGE, FinancialMetricKey.GROSS_PROFIT, FinancialMetricKey.REVENUE, "percent"),
    _CalculationSpec(CalculationKey.OPERATING_PROFIT_MARGIN, "Operating profit margin", "(Operating Income / Revenue) × 100", CalculationUnit.PERCENTAGE, FinancialMetricKey.OPERATING_INCOME, FinancialMetricKey.REVENUE, "percent"),
    _CalculationSpec(CalculationKey.NET_PROFIT_MARGIN, "Net profit margin", "(Net Income / Revenue) × 100; when only Net Loss is reported, (-ABS(Net Loss) / Revenue) × 100", CalculationUnit.PERCENTAGE, FinancialMetricKey.NET_INCOME, FinancialMetricKey.REVENUE, "net_margin"),
    _CalculationSpec(CalculationKey.EBITDA_MARGIN, "EBITDA margin", "(EBITDA / Revenue) × 100", CalculationUnit.PERCENTAGE, FinancialMetricKey.EBITDA, FinancialMetricKey.REVENUE, "percent"),
    _CalculationSpec(CalculationKey.CURRENT_RATIO, "Current ratio", "Current Assets / Current Liabilities", CalculationUnit.RATIO, FinancialMetricKey.CURRENT_ASSETS, FinancialMetricKey.CURRENT_LIABILITIES, "ratio"),
    _CalculationSpec(CalculationKey.CASH_RATIO, "Cash ratio", "Cash and Cash Equivalents / Current Liabilities", CalculationUnit.RATIO, FinancialMetricKey.CASH_AND_EQUIVALENTS, FinancialMetricKey.CURRENT_LIABILITIES, "ratio"),
    _CalculationSpec(CalculationKey.NET_WORKING_CAPITAL, "Net working capital", "Current Assets - Current Liabilities", CalculationUnit.CURRENCY_AMOUNT, FinancialMetricKey.CURRENT_ASSETS, FinancialMetricKey.CURRENT_LIABILITIES, "difference"),
    _CalculationSpec(CalculationKey.DEBT_TO_EQUITY_RATIO, "Debt-to-equity ratio", "Total Debt / Shareholders' Equity", CalculationUnit.RATIO, FinancialMetricKey.TOTAL_DEBT, FinancialMetricKey.SHAREHOLDERS_EQUITY, "ratio"),
    _CalculationSpec(CalculationKey.LIABILITIES_TO_ASSETS_RATIO, "Liabilities-to-assets ratio", "(Total Liabilities / Total Assets) × 100", CalculationUnit.PERCENTAGE, FinancialMetricKey.TOTAL_LIABILITIES, FinancialMetricKey.TOTAL_ASSETS, "percent"),
    _CalculationSpec(CalculationKey.OPERATING_CASH_FLOW_MARGIN, "Operating cash flow margin", "(Operating Cash Flow / Revenue) × 100", CalculationUnit.PERCENTAGE, FinancialMetricKey.OPERATING_CASH_FLOW, FinancialMetricKey.REVENUE, "percent"),
    _CalculationSpec(CalculationKey.FREE_CASH_FLOW_MARGIN, "Free cash flow margin", "(Reported Free Cash Flow / Revenue) × 100", CalculationUnit.PERCENTAGE, FinancialMetricKey.FREE_CASH_FLOW, FinancialMetricKey.REVENUE, "percent"),
)


_USED_KEYS = {
    key
    for spec in _PAIR_SPECS
    for key in (spec.first_input, spec.second_input)
} | {FinancialMetricKey.CAPITAL_EXPENDITURE, FinancialMetricKey.NET_LOSS}


def calculate_financial_metrics(metrics: Iterable[FinancialMetric]) -> FinancialCalculationResult:
    """Calculate supported indicators without mutating input metrics.

    Monetary inputs require an explicit matching currency code and compatible
    period. Calculations never fetch data, write to storage, or infer values.
    """
    inputs = [metric.model_copy(deep=True) for metric in metrics]
    result = FinancialCalculationResult()
    period_keys = {_period_key(metric) for metric in inputs if metric.metric_key in _USED_KEYS}
    if not period_keys:
        period_keys = {None}

    for period_key in sorted(period_keys, key=lambda value: repr(value)):
        period_records = [metric for metric in inputs
                          if metric.metric_key in _USED_KEYS and _period_key(metric) == period_key]
        for spec in _PAIR_SPECS:
            calculation = _calculate_pair(spec, inputs, period_key, period_records)
            _store(result, calculation)

        _store(result, _calculate_free_cash_flow(inputs, period_key, period_records))

    growth_years = sorted({year for metric in inputs if metric.metric_key == FinancialMetricKey.REVENUE
                           if (year := _annual_year(metric)) is not None})
    if not growth_years:
        _store(result, _unavailable(
            CalculationKey.ANNUAL_REVENUE_GROWTH,
            "Annual revenue growth",
            "((Current Year Revenue - Previous Year Revenue) / Previous Year Revenue) × 100",
            CalculationUnit.PERCENTAGE,
            reason="No annual revenue with a recognizable fiscal year was supplied.",
        ))
    else:
        for year in growth_years:
            _store(result, _calculate_revenue_growth(inputs, year))
    return result


def _calculate_pair(spec: _CalculationSpec, metrics: Sequence[FinancialMetric],
                    period_key: Optional[Tuple], period_records: Sequence[FinancialMetric]) -> FinancialCalculation:
    first = _select(metrics, spec.first_input, period_key)
    second = _select(metrics, spec.second_input, period_key)
    selections = [first, second]
    used = [record for selection in selections for record in selection.records]

    if first.ambiguous or second.ambiguous:
        return _ambiguous(spec.key, spec.name, spec.formula, spec.unit, used,
                          first.problem or second.problem or "Conflicting source figures were found.", period_records)

    if spec.operation == "net_margin":
        loss = _select(metrics, FinancialMetricKey.NET_LOSS, period_key)
        if loss.records and loss.problem:
            return _ambiguous(spec.key, spec.name, spec.formula, spec.unit, used + loss.records, loss.problem, period_records)
        if first.records and loss.records:
            return _ambiguous(spec.key, spec.name, spec.formula, spec.unit, used + loss.records,
                              "Both net income and net loss are reported for this period.", period_records)
        if not first.records:
            first = loss
            used = [record for selection in (first, second) for record in selection.records]
            if first.record is not None:
                numerator = -abs(first.record.normalized_value)
            else:
                numerator = None
        else:
            numerator = first.record.normalized_value if first.record else None
    else:
        numerator = first.record.normalized_value if first.record else None

    missing = [
        selection for selection in (first, second)
        if selection.record is None and not selection.ambiguous
    ]
    if missing:
        used.extend(_other_period_inputs(metrics, (spec.first_input, spec.second_input), period_key))
        if spec.operation == "net_margin" and first.record is None:
            reason = "The calculation requires revenue and either net income or net loss; no numerator is available for this period."
        else:
            reason = _missing_reason(metrics, (spec.first_input, spec.second_input), period_key)
        return _unavailable(spec.key, spec.name, spec.formula, spec.unit, used, reason, period_records)
    if period_key is None:
        return _unavailable(spec.key, spec.name, spec.formula, spec.unit, used,
                            "Inputs do not identify a compatible reporting period.", period_records)
    actuality_problem = _actuality_problem(first.record, second.record)
    if actuality_problem:
        return _ambiguous(spec.key, spec.name, spec.formula, spec.unit, used, actuality_problem, period_records)
    currency_problem, currency_ambiguous = _currency_problem((first.record, second.record))
    if currency_problem:
        constructor = _ambiguous if currency_ambiguous else _unavailable
        return constructor(spec.key, spec.name, spec.formula, spec.unit, used, currency_problem, period_records)
    if not _is_usable(first.record) or not _is_usable(second.record):
        return _ambiguous(spec.key, spec.name, spec.formula, spec.unit, used,
                          "At least one input is not a resolved extracted numeric value.", period_records)

    denominator = second.record.normalized_value
    if spec.operation in {"percent", "ratio", "net_margin"} and denominator == 0:
        return _unavailable(spec.key, spec.name, spec.formula, spec.unit, used,
                            "The denominator is zero; division is unavailable.", period_records)
    try:
        if spec.operation in {"percent", "ratio", "net_margin"}:
            with localcontext() as context:
                context.prec = 28
                value = numerator / denominator
                if spec.operation in {"percent", "net_margin"}:
                    value *= Decimal(100)
                    value = value.quantize(_PERCENT_QUANTUM, rounding=ROUND_HALF_UP)
                else:
                    value = value.quantize(_RATIO_QUANTUM, rounding=ROUND_HALF_UP)
        else:
            value = first.record.normalized_value - second.record.normalized_value
    except (ArithmeticError, ValueError):
        return _unavailable(spec.key, spec.name, spec.formula, spec.unit, used,
                            "The inputs could not be combined with Decimal arithmetic.", period_records)
    return _calculated(spec.key, spec.name, value, spec.unit, spec.formula, used, period_records)


def _calculate_free_cash_flow(metrics: Sequence[FinancialMetric], period_key: Optional[Tuple],
                              period_records: Sequence[FinancialMetric]) -> FinancialCalculation:
    key = CalculationKey.FREE_CASH_FLOW
    name = "Free cash flow"
    formula = "Reported Free Cash Flow; otherwise Operating Cash Flow - ABS(Capital Expenditure)"
    explicit = _select(metrics, FinancialMetricKey.FREE_CASH_FLOW, period_key)
    if explicit.ambiguous:
        return _ambiguous(key, name, formula, CalculationUnit.CURRENCY_AMOUNT, explicit.records,
                          explicit.problem or "Conflicting reported free cash flow values were found.", period_records)
    if explicit.record:
        if period_key is None:
            return _unavailable(key, name, formula, CalculationUnit.CURRENCY_AMOUNT, explicit.records,
                                "The reported free cash flow has no explicit reporting period.", period_records)
        if not _is_usable(explicit.record):
            return _ambiguous(key, name, formula, CalculationUnit.CURRENCY_AMOUNT, explicit.records,
                              "Reported free cash flow is not a resolved extracted value.", period_records)
        return _calculated(key, name, explicit.record.normalized_value, CalculationUnit.CURRENCY_AMOUNT,
                           "Reported Free Cash Flow", explicit.records, period_records)

    operating = _select(metrics, FinancialMetricKey.OPERATING_CASH_FLOW, period_key)
    capex = _select(metrics, FinancialMetricKey.CAPITAL_EXPENDITURE, period_key)
    used = operating.records + capex.records
    if operating.ambiguous or capex.ambiguous:
        return _ambiguous(key, name, formula, CalculationUnit.CURRENCY_AMOUNT, used,
                          operating.problem or capex.problem or "Conflicting source figures were found.", period_records)
    if operating.record is None or capex.record is None:
        used.extend(_other_period_inputs(
            metrics,
            (FinancialMetricKey.OPERATING_CASH_FLOW, FinancialMetricKey.CAPITAL_EXPENDITURE),
            period_key,
        ))
        reason = _missing_reason(metrics, (FinancialMetricKey.OPERATING_CASH_FLOW,
                                           FinancialMetricKey.CAPITAL_EXPENDITURE), period_key)
        return _unavailable(key, name, formula, CalculationUnit.CURRENCY_AMOUNT, used, reason, period_records)
    if period_key is None:
        return _unavailable(key, name, formula, CalculationUnit.CURRENCY_AMOUNT, used,
                            "Inputs do not identify a compatible reporting period.", period_records)
    actuality_problem = _actuality_problem(operating.record, capex.record)
    if actuality_problem:
        return _ambiguous(key, name, formula, CalculationUnit.CURRENCY_AMOUNT, used, actuality_problem, period_records)
    currency_problem, currency_ambiguous = _currency_problem((operating.record, capex.record))
    if currency_problem:
        constructor = _ambiguous if currency_ambiguous else _unavailable
        return constructor(key, name, formula, CalculationUnit.CURRENCY_AMOUNT, used, currency_problem, period_records)
    if not _is_usable(operating.record) or not _is_usable(capex.record):
        return _ambiguous(key, name, formula, CalculationUnit.CURRENCY_AMOUNT, used,
                          "At least one input is not a resolved extracted numeric value.", period_records)
    value = operating.record.normalized_value - abs(capex.record.normalized_value)
    return _calculated(key, name, value, CalculationUnit.CURRENCY_AMOUNT, formula, used, period_records)


def _calculate_revenue_growth(metrics: Sequence[FinancialMetric], year: int) -> FinancialCalculation:
    key = CalculationKey.ANNUAL_REVENUE_GROWTH
    name = "Annual revenue growth"
    formula = "((Current Year Revenue - Previous Year Revenue) / Previous Year Revenue) × 100"
    current = _select_annual_revenue(metrics, year)
    previous = _select_annual_revenue(metrics, year - 1)
    used = current.records + previous.records
    if current.ambiguous or previous.ambiguous:
        return _ambiguous(key, name, formula, CalculationUnit.PERCENTAGE, used,
                          current.problem or previous.problem or "Conflicting annual revenue figures were found.",
                          current.records)
    if current.record is None or previous.record is None:
        missing_year = year if current.record is None else year - 1
        candidates = [metric for metric in metrics if metric.metric_key == FinancialMetricKey.REVENUE
                      and _annual_year(metric) == missing_year]
        if candidates:
            if not any(_is_annual(metric) for metric in candidates):
                return _unavailable(key, name, formula, CalculationUnit.PERCENTAGE, used + candidates,
                                    f"Only quarterly or partial revenue is available for FY{missing_year}; an annual figure is required.",
                                    current.records)
            return _unavailable(key, name, formula, CalculationUnit.PERCENTAGE, used + candidates,
                                f"FY{missing_year} revenue is not explicitly marked as actual.", current.records)
        return _unavailable(key, name, formula, CalculationUnit.PERCENTAGE, used,
                            f"Actual annual revenue for FY{missing_year} is missing; consecutive years are required.",
                            current.records)
    if current.record.normalized_value is None or previous.record.normalized_value is None:
        return _ambiguous(key, name, formula, CalculationUnit.PERCENTAGE, used,
                          "An annual revenue input is not a resolved numeric value.", current.records)
    if current.record.normalized_value is not None and previous.record.normalized_value == 0:
        return _unavailable(key, name, formula, CalculationUnit.PERCENTAGE, used,
                            "Previous-year revenue is zero; growth is undefined.", current.records)
    currency_problem, currency_ambiguous = _currency_problem((current.record, previous.record))
    if currency_problem:
        constructor = _ambiguous if currency_ambiguous else _unavailable
        return constructor(key, name, formula, CalculationUnit.PERCENTAGE, used, currency_problem, current.records)
    if current.record.actuality != "actual" or previous.record.actuality != "actual":
        return _unavailable(key, name, formula, CalculationUnit.PERCENTAGE, used,
                            "Annual growth requires actual revenue for both consecutive fiscal years.", current.records)
    try:
        with localcontext() as context:
            context.prec = 28
            value = ((current.record.normalized_value - previous.record.normalized_value)
                     / previous.record.normalized_value * Decimal(100))
            value = value.quantize(_PERCENT_QUANTUM, rounding=ROUND_HALF_UP)
    except (ArithmeticError, ValueError):
        return _unavailable(key, name, formula, CalculationUnit.PERCENTAGE, used,
                            "Annual growth could not be calculated with Decimal arithmetic.", current.records)
    return _calculated(key, name, value, CalculationUnit.PERCENTAGE, formula, used, current.records)


def _select(metrics: Sequence[FinancialMetric], key: FinancialMetricKey,
            period_key: Optional[Tuple]) -> _Selection:
    candidates = [metric for metric in metrics if metric.metric_key == key and _period_key(metric) == period_key]
    return _selection(candidates)


def _select_annual_revenue(metrics: Sequence[FinancialMetric], year: int) -> _Selection:
    all_year_candidates = [metric for metric in metrics if metric.metric_key == FinancialMetricKey.REVENUE
                           and _annual_year(metric) == year]
    candidates = [metric for metric in all_year_candidates if _is_annual(metric)]
    if not candidates:
        if all_year_candidates:
            return _Selection(all_year_candidates, problem=f"FY{year} has only quarterly or partial revenue, not an annual figure.")
        return _Selection([])
    actuals = [metric for metric in candidates if _actuality(metric) == "actual"]
    if not actuals:
        return _Selection(candidates, problem=f"FY{year} revenue is not explicitly marked as actual.")
    if len(actuals) != len(candidates):
        return _Selection(candidates, problem=f"FY{year} includes both actual and forecast revenue.", ambiguous=True)
    selection = _selection(actuals)
    if selection.record and (selection.record.fiscal_quarter is not None):
        return _Selection(candidates, problem=f"FY{year} revenue is not an annual figure.")
    return selection


def _selection(candidates: List[FinancialMetric]) -> _Selection:
    if not candidates:
        return _Selection([])
    if any(metric.normalized_unit and metric.normalized_unit.casefold() not in {"currency", "currency_amount"}
           for metric in candidates):
        return _Selection(candidates, problem="A candidate input is not a currency amount.", ambiguous=True)
    if any(not _is_usable(metric) for metric in candidates):
        return _Selection(candidates, problem="At least one candidate metric is ambiguous or unresolved.", ambiguous=True)
    identities = {
        (metric.normalized_value, metric.currency_code,
         metric.currency_symbol if metric.currency_code is None else None,
         _actuality(metric))
        for metric in candidates
    }
    if len(identities) > 1:
        return _Selection(candidates, problem="Conflicting figures were found for the same metric and period.", ambiguous=True)
    return _Selection(candidates, record=candidates[0])


def _is_usable(metric: FinancialMetric) -> bool:
    status = metric.extraction_status.value if hasattr(metric.extraction_status, "value") else str(metric.extraction_status)
    unit = metric.normalized_unit.casefold() if metric.normalized_unit else None
    return (
        metric.normalized_value is not None
        and status.lower() == "extracted"
        and unit in {None, "currency", "currency_amount"}
    )


def _actuality(metric: FinancialMetric) -> Optional[str]:
    return metric.actuality.strip().lower() if metric.actuality else None


def _actuality_problem(first: FinancialMetric, second: FinancialMetric) -> Optional[str]:
    if _actuality(first) != _actuality(second):
        return "Inputs mix actual, forecast, target, or unspecified figures."
    return None


def _currency_problem(metrics: Sequence[FinancialMetric]) -> Tuple[Optional[str], bool]:
    codes = [metric.currency_code.upper() if metric.currency_code else None for metric in metrics]
    if any(code is None for code in codes):
        return "A matching explicit currency code is required; symbols such as $ are ambiguous.", False
    if len(set(codes)) != 1:
        return "Inputs use different currency codes and cannot be combined.", True
    return None, False


def _period_key(metric: FinancialMetric) -> Optional[Tuple]:
    if metric.period_start_date or metric.period_end_date:
        return ("dates", metric.period_start_date, metric.period_end_date)
    year = _annual_year(metric)
    if year is not None:
        return ("fiscal", year, metric.fiscal_quarter)
    if metric.reporting_period_label:
        label = re.sub(r"\s+", " ", metric.reporting_period_label.strip()).casefold()
        return ("label", label)
    return None


def _is_annual(metric: FinancialMetric) -> bool:
    if metric.fiscal_quarter is not None or _annual_year(metric) is None:
        return False
    label = (metric.reporting_period_label or "").casefold()
    if re.search(r"\bq[1-4]\b|\bquarter|\bqtr|\bh[12]\b|half[- ]?year|six months", label):
        return False
    if metric.period_start_date and metric.period_end_date:
        duration_days = (metric.period_end_date - metric.period_start_date).days
        if duration_days < 330 or duration_days > 400:
            return False
    return True


def _annual_year(metric: FinancialMetric) -> Optional[int]:
    if metric.fiscal_year is not None:
        return metric.fiscal_year
    label = metric.reporting_period_label or ""
    match = re.fullmatch(r"\s*(?:FY|CY|fiscal year|calendar year)?\s*((?:19|20)\d{2})\s*", label, re.I)
    return int(match.group(1)) if match else None


def _period_label(metrics: Sequence[FinancialMetric]) -> Optional[str]:
    for metric in metrics:
        if metric.reporting_period_label:
            return metric.reporting_period_label
    if metrics and metrics[0].fiscal_year is not None:
        year = metrics[0].fiscal_year
        return f"Q{metrics[0].fiscal_quarter} FY{year}" if metrics[0].fiscal_quarter else f"FY{year}"
    if metrics and metrics[0].period_start_date and metrics[0].period_end_date:
        return f"{metrics[0].period_start_date.isoformat()} to {metrics[0].period_end_date.isoformat()}"
    return None


def _missing_reason(metrics: Sequence[FinancialMetric], keys: Sequence[FinancialMetricKey],
                    period_key: Optional[Tuple]) -> str:
    missing: List[FinancialMetricKey] = []
    different_periods: List[FinancialMetricKey] = []
    for key in keys:
        same_period = [metric for metric in metrics if metric.metric_key == key and _period_key(metric) == period_key]
        if same_period:
            continue
        other_period = [metric for metric in metrics if metric.metric_key == key]
        if other_period:
            different_periods.append(key)
        else:
            missing.append(key)
    if different_periods:
        labels = ", ".join(key.value for key in different_periods)
        return f"Required inputs exist only for a different reporting period: {labels}."
    if missing:
        labels = ", ".join(key.value for key in missing)
        return f"Required financial input is missing: {labels}."
    return "Required compatible inputs are unavailable."


def _other_period_inputs(metrics: Sequence[FinancialMetric], keys: Sequence[FinancialMetricKey],
                         period_key: Optional[Tuple]) -> List[FinancialMetric]:
    missing_keys = {
        key for key in keys
        if not any(metric.metric_key == key and _period_key(metric) == period_key for metric in metrics)
    }
    return [metric for metric in metrics
            if metric.metric_key in missing_keys and _period_key(metric) != period_key]


def _to_input(metric: FinancialMetric) -> CalculationInput:
    return CalculationInput(
        metric_key=metric.metric_key,
        original_metric_label=metric.original_metric_label,
        original_value=(
            metric.original_numeric_value or str(metric.normalized_value)
            if metric.normalized_value is not None
            else metric.original_numeric_value
        ),
        normalized_value=metric.normalized_value,
        currency_code=metric.currency_code,
        currency_symbol=metric.currency_symbol,
        original_unit_scale=metric.original_unit_scale,
        normalized_unit=metric.normalized_unit,
        reporting_period_label=metric.reporting_period_label,
        period_start_date=metric.period_start_date,
        period_end_date=metric.period_end_date,
        fiscal_year=metric.fiscal_year,
        fiscal_quarter=metric.fiscal_quarter,
        actuality=metric.actuality,
        source_evidence_id=metric.source_evidence_id,
        source_url=metric.source_url,
        source_title=metric.source_title,
        supporting_excerpt=metric.supporting_excerpt,
        evidence_verification_status=metric.evidence_verification_status,
        extraction_status=metric.extraction_status,
    )


def _calculated(key: CalculationKey, name: str, value: Decimal, unit: CalculationUnit,
                formula: str, metrics: Sequence[FinancialMetric],
                period_records: Sequence[FinancialMetric]) -> FinancialCalculation:
    return _build(key, name, value, unit, formula, metrics, period_records,
                  CalculationStatus.CALCULATED, None)


def _unavailable(key: CalculationKey, name: str, formula: str, unit: CalculationUnit,
                 metrics: Sequence[FinancialMetric] = (), reason: str = "Required inputs are unavailable.",
                 period_records: Sequence[FinancialMetric] = ()) -> FinancialCalculation:
    return _build(key, name, None, unit, formula, metrics, period_records,
                  CalculationStatus.UNAVAILABLE, reason)


def _ambiguous(key: CalculationKey, name: str, formula: str, unit: CalculationUnit,
               metrics: Sequence[FinancialMetric], reason: str,
               period_records: Sequence[FinancialMetric]) -> FinancialCalculation:
    return _build(key, name, None, unit, formula, metrics, period_records,
                  CalculationStatus.AMBIGUOUS, reason)


def _build(key: CalculationKey, name: str, value: Optional[Decimal], unit: CalculationUnit,
           formula: str, metrics: Sequence[FinancialMetric], period_records: Sequence[FinancialMetric],
           status: CalculationStatus, explanation: Optional[str]) -> FinancialCalculation:
    unique: List[FinancialMetric] = []
    seen = set()
    for metric in metrics:
        identity = (metric.source_evidence_id, metric.source_url, metric.metric_key,
                    metric.original_numeric_value, metric.normalized_value,
                    metric.currency_code, metric.currency_symbol, metric.extraction_status,
                    metric.reporting_period_label, metric.actuality, metric.supporting_excerpt)
        if identity not in seen:
            unique.append(metric)
            seen.add(identity)
    inputs = [_to_input(metric) for metric in unique]
    source_ids = list(dict.fromkeys(item.source_evidence_id for item in inputs))
    source_urls = list(dict.fromkeys(item.source_url for item in inputs))
    excerpts = list(dict.fromkeys(item.supporting_excerpt for item in inputs))
    codes = {item.currency_code for item in inputs}
    symbols = {item.currency_symbol for item in inputs}
    currency_code = next(iter(codes)) if len(codes) == 1 else None
    currency_symbol = next(iter(symbols)) if len(symbols) == 1 else None
    actuality_values = {item.actuality for item in inputs}
    actuality = next(iter(actuality_values)) if len(actuality_values) == 1 else None
    label = _period_label(period_records) or _period_label(unique)
    fiscal_year = next((item.fiscal_year for item in period_records if item.fiscal_year is not None), None)
    fiscal_quarter = next((item.fiscal_quarter for item in period_records if item.fiscal_quarter is not None), None)
    start_date = next((item.period_start_date for item in period_records if item.period_start_date is not None), None)
    end_date = next((item.period_end_date for item in period_records if item.period_end_date is not None), None)
    return FinancialCalculation(
        calculation_key=key,
        calculation_name=name,
        value=value,
        unit=unit,
        formula=formula,
        input_metrics=inputs,
        reporting_period_label=label,
        period_start_date=start_date,
        period_end_date=end_date,
        fiscal_year=fiscal_year,
        fiscal_quarter=fiscal_quarter,
        actuality=actuality,
        currency_code=currency_code,
        currency_symbol=currency_symbol,
        source_evidence_ids=source_ids,
        source_urls=source_urls,
        supporting_excerpts=excerpts,
        evidence_verification_status=_verification_status(inputs),
        status=status,
        explanation=explanation,
    )


def _verification_status(inputs: Sequence[CalculationInput]) -> str:
    if not inputs:
        return "unavailable"
    statuses = {item.evidence_verification_status.strip().lower() for item in inputs}
    if any(status not in {"verified", "partially_verified", "unverified"} for status in statuses):
        return "unverified"
    if "unverified" in statuses:
        return "unverified"
    if "partially_verified" in statuses:
        return "partially_verified"
    return "verified"


def _store(result: FinancialCalculationResult, calculation: FinancialCalculation) -> None:
    if calculation.status == CalculationStatus.CALCULATED:
        result.calculated.append(calculation)
    elif calculation.status == CalculationStatus.AMBIGUOUS:
        result.ambiguous.append(calculation)
    else:
        result.unavailable.append(calculation)
