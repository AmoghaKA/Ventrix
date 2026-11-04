import unittest
from datetime import date
from decimal import Decimal

from app.financial import (
    CalculationKey,
    CalculationStatus,
    CalculationUnit,
    ExtractionStatus,
    FinancialMetric,
    FinancialMetricKey,
    calculate_financial_metrics,
)


def metric(key, value, *, year=2024, quarter=None, label=None, currency="USD",
           symbol="$", actuality="actual", verified="verified", evidence_id=1,
           extraction_status=ExtractionStatus.EXTRACTED, start=None, end=None):
    number = Decimal(str(value)) if value is not None else None
    return FinancialMetric(
        metric_key=key,
        original_metric_label=key.value.replace("_", " ").title(),
        normalized_value=number,
        original_numeric_value=str(value) if value is not None else None,
        currency_code=currency,
        currency_symbol=symbol,
        normalized_unit="currency",
        reporting_period_label=label or (f"Q{quarter} FY{year}" if quarter else f"FY{year}"),
        fiscal_year=year,
        fiscal_quarter=quarter,
        period_start_date=start,
        period_end_date=end,
        source_evidence_id=evidence_id,
        source_url=f"https://example.test/evidence/{evidence_id}",
        source_title=f"Synthetic source {evidence_id}",
        supporting_excerpt=f"Synthetic {key.value} statement for FY{year}: {value}.",
        evidence_verification_status=verified,
        extraction_status=extraction_status,
        actuality=actuality,
    )


def find(result, key, *, status=None, year=2024):
    groups = (result.calculated, result.unavailable, result.ambiguous)
    for calculation in (item for group in groups for item in group):
        if calculation.calculation_key != key:
            continue
        if status is not None and calculation.status != status:
            continue
        if year is not None and calculation.fiscal_year != year:
            continue
        return calculation
    raise AssertionError(f"No calculation found: {key} {status} FY{year}")


def base_metrics(year=2024):
    return [
        metric(FinancialMetricKey.REVENUE, "10000000", year=year, evidence_id=1),
        metric(FinancialMetricKey.GROSS_PROFIT, "6000000", year=year, evidence_id=2),
        metric(FinancialMetricKey.OPERATING_INCOME, "2000000", year=year, evidence_id=3),
        metric(FinancialMetricKey.NET_INCOME, "1000000", year=year, evidence_id=4),
        metric(FinancialMetricKey.EBITDA, "3000000", year=year, evidence_id=5),
        metric(FinancialMetricKey.CURRENT_ASSETS, "9000000", year=year, evidence_id=6),
        metric(FinancialMetricKey.CURRENT_LIABILITIES, "3000000", year=year, evidence_id=7),
        metric(FinancialMetricKey.CASH_AND_EQUIVALENTS, "1500000", year=year, evidence_id=8),
        metric(FinancialMetricKey.TOTAL_DEBT, "2000000", year=year, evidence_id=9),
        metric(FinancialMetricKey.SHAREHOLDERS_EQUITY, "4000000", year=year, evidence_id=10),
        metric(FinancialMetricKey.TOTAL_LIABILITIES, "5000000", year=year, evidence_id=11),
        metric(FinancialMetricKey.TOTAL_ASSETS, "10000000", year=year, evidence_id=12),
        metric(FinancialMetricKey.OPERATING_CASH_FLOW, "2500000", year=year, evidence_id=13),
        metric(FinancialMetricKey.FREE_CASH_FLOW, "1500000", year=year, evidence_id=14),
        metric(FinancialMetricKey.CAPITAL_EXPENDITURE, "800000", year=year, evidence_id=15),
    ]


class FinancialCalculationTests(unittest.TestCase):
    def test_profitability_indicators_use_decimal_arithmetic(self):
        result = calculate_financial_metrics(base_metrics())
        expected = {
            CalculationKey.GROSS_PROFIT_MARGIN: Decimal("60.00"),
            CalculationKey.OPERATING_PROFIT_MARGIN: Decimal("20.00"),
            CalculationKey.NET_PROFIT_MARGIN: Decimal("10.00"),
            CalculationKey.EBITDA_MARGIN: Decimal("30.00"),
        }
        for key, value in expected.items():
            self.assertEqual(find(result, key).value, value)
            self.assertEqual(find(result, key).unit, CalculationUnit.PERCENTAGE)

    def test_net_loss_is_a_negative_numerator_when_net_income_is_missing(self):
        inputs = [
            metric(FinancialMetricKey.REVENUE, "10000000", evidence_id=1),
            metric(FinancialMetricKey.NET_LOSS, "2000000", evidence_id=2),
        ]
        calculation = find(calculate_financial_metrics(inputs), CalculationKey.NET_PROFIT_MARGIN)
        self.assertEqual(calculation.value, Decimal("-20.00"))
        self.assertEqual(calculation.input_metrics[0].metric_key, FinancialMetricKey.NET_LOSS)

    def test_both_net_income_and_net_loss_are_ambiguous(self):
        inputs = [
            metric(FinancialMetricKey.REVENUE, "10", evidence_id=1),
            metric(FinancialMetricKey.NET_INCOME, "2", evidence_id=2),
            metric(FinancialMetricKey.NET_LOSS, "2", evidence_id=3),
        ]
        calculation = find(calculate_financial_metrics(inputs), CalculationKey.NET_PROFIT_MARGIN,
                           status=CalculationStatus.AMBIGUOUS)
        self.assertIn(2, calculation.source_evidence_ids)
        self.assertIn(3, calculation.source_evidence_ids)

    def test_liquidity_indicators(self):
        result = calculate_financial_metrics(base_metrics())
        self.assertEqual(find(result, CalculationKey.CURRENT_RATIO).value, Decimal("3.0000"))
        self.assertEqual(find(result, CalculationKey.CASH_RATIO).value, Decimal("0.5000"))
        working_capital = find(result, CalculationKey.NET_WORKING_CAPITAL)
        self.assertEqual(working_capital.value, Decimal("6000000"))
        self.assertEqual(working_capital.unit, CalculationUnit.CURRENCY_AMOUNT)

    def test_leverage_indicators_keep_debt_and_liabilities_distinct(self):
        result = calculate_financial_metrics(base_metrics())
        self.assertEqual(find(result, CalculationKey.DEBT_TO_EQUITY_RATIO).value, Decimal("0.5000"))
        liabilities = find(result, CalculationKey.LIABILITIES_TO_ASSETS_RATIO)
        self.assertEqual(liabilities.value, Decimal("50.00"))
        self.assertIn(FinancialMetricKey.TOTAL_LIABILITIES, [item.metric_key for item in liabilities.input_metrics])
        self.assertNotIn(FinancialMetricKey.TOTAL_DEBT, [item.metric_key for item in liabilities.input_metrics])

    def test_cash_flow_margins_and_explicit_free_cash_flow(self):
        result = calculate_financial_metrics(base_metrics())
        self.assertEqual(find(result, CalculationKey.OPERATING_CASH_FLOW_MARGIN).value, Decimal("25.00"))
        self.assertEqual(find(result, CalculationKey.FREE_CASH_FLOW_MARGIN).value, Decimal("15.00"))
        free_cash_flow = find(result, CalculationKey.FREE_CASH_FLOW)
        self.assertEqual(free_cash_flow.value, Decimal("1500000"))
        self.assertEqual(free_cash_flow.formula, "Reported Free Cash Flow")

    def test_derives_free_cash_flow_from_compatible_inputs(self):
        inputs = [
            metric(FinancialMetricKey.OPERATING_CASH_FLOW, "2500000", evidence_id=13),
            metric(FinancialMetricKey.CAPITAL_EXPENDITURE, "800000", evidence_id=15),
        ]
        calculation = find(calculate_financial_metrics(inputs), CalculationKey.FREE_CASH_FLOW)
        self.assertEqual(calculation.value, Decimal("1700000"))
        self.assertIn("ABS(Capital Expenditure)", calculation.formula)
        self.assertEqual(set(calculation.source_evidence_ids), {13, 15})

    def test_derived_free_cash_flow_rejects_currency_or_period_mismatch(self):
        currency_inputs = [
            metric(FinancialMetricKey.OPERATING_CASH_FLOW, "100", currency="USD", evidence_id=13),
            metric(FinancialMetricKey.CAPITAL_EXPENDITURE, "30", currency="INR", evidence_id=15),
        ]
        calc = find(calculate_financial_metrics(currency_inputs), CalculationKey.FREE_CASH_FLOW,
                    status=CalculationStatus.AMBIGUOUS)
        self.assertIn("different currency", calc.explanation)
        period_inputs = [
            metric(FinancialMetricKey.OPERATING_CASH_FLOW, "100", year=2024, evidence_id=13),
            metric(FinancialMetricKey.CAPITAL_EXPENDITURE, "30", year=2023, evidence_id=15),
        ]
        calc = find(calculate_financial_metrics(period_inputs), CalculationKey.FREE_CASH_FLOW,
                    year=2024, status=CalculationStatus.UNAVAILABLE)
        self.assertIn("different reporting period", calc.explanation)
        self.assertEqual(set(calc.source_evidence_ids), {13, 15})

    def test_uses_absolute_value_for_negative_capital_expenditure(self):
        inputs = [
            metric(FinancialMetricKey.OPERATING_CASH_FLOW, "100", evidence_id=13),
            metric(FinancialMetricKey.CAPITAL_EXPENDITURE, "-30", evidence_id=15),
        ]
        self.assertEqual(find(calculate_financial_metrics(inputs), CalculationKey.FREE_CASH_FLOW).value,
                         Decimal("70"))

    def test_revenue_growth_uses_consecutive_actual_annual_periods(self):
        inputs = [
            metric(FinancialMetricKey.REVENUE, "8000000", year=2023, evidence_id=20),
            metric(FinancialMetricKey.REVENUE, "10000000", year=2024, evidence_id=21),
        ]
        calculation = find(calculate_financial_metrics(inputs), CalculationKey.ANNUAL_REVENUE_GROWTH)
        self.assertEqual(calculation.value, Decimal("25.00"))
        self.assertEqual(calculation.actuality, "actual")

    def test_revenue_growth_requires_consecutive_years(self):
        inputs = [
            metric(FinancialMetricKey.REVENUE, "8", year=2022, evidence_id=20),
            metric(FinancialMetricKey.REVENUE, "10", year=2024, evidence_id=21),
        ]
        calculation = find(calculate_financial_metrics(inputs), CalculationKey.ANNUAL_REVENUE_GROWTH,
                           year=2024, status=CalculationStatus.UNAVAILABLE)
        self.assertIn("FY2023", calculation.explanation)

    def test_revenue_growth_rejects_forecasts_and_quarterly_values(self):
        forecast = [
            metric(FinancialMetricKey.REVENUE, "8", year=2023, actuality="actual", evidence_id=20),
            metric(FinancialMetricKey.REVENUE, "10", year=2024, actuality="forecast_or_target", evidence_id=21),
        ]
        calc = find(calculate_financial_metrics(forecast), CalculationKey.ANNUAL_REVENUE_GROWTH,
                    year=2024, status=CalculationStatus.UNAVAILABLE)
        self.assertIn("actual", calc.explanation.lower())
        quarterly = [
            metric(FinancialMetricKey.REVENUE, "8", year=2023, evidence_id=20),
            metric(FinancialMetricKey.REVENUE, "10", year=2024, quarter=1, evidence_id=21),
        ]
        calc = find(calculate_financial_metrics(quarterly), CalculationKey.ANNUAL_REVENUE_GROWTH,
                    year=2024, status=CalculationStatus.UNAVAILABLE)
        self.assertIn("quarter", calc.explanation.lower())
        period_label_only = [
            metric(FinancialMetricKey.REVENUE, "8", year=2023, evidence_id=20),
            metric(FinancialMetricKey.REVENUE, "10", year=2024, quarter=None,
                   label="Q1 FY2024", evidence_id=21),
        ]
        calc = find(calculate_financial_metrics(period_label_only), CalculationKey.ANNUAL_REVENUE_GROWTH,
                    year=2024, status=CalculationStatus.UNAVAILABLE)
        self.assertIn("quarter", calc.explanation.lower())

    def test_revenue_growth_rejects_a_short_period_marked_with_a_fiscal_year(self):
        inputs = [
            metric(FinancialMetricKey.REVENUE, "8", year=2023, evidence_id=20),
            metric(FinancialMetricKey.REVENUE, "10", year=2024, evidence_id=21,
                   start=date(2024, 1, 1), end=date(2024, 6, 30)),
        ]
        calculation = find(calculate_financial_metrics(inputs), CalculationKey.ANNUAL_REVENUE_GROWTH,
                           year=2024, status=CalculationStatus.UNAVAILABLE)
        self.assertIn("annual figure", calculation.explanation.lower())

    def test_revenue_growth_rejects_zero_previous_year(self):
        inputs = [
            metric(FinancialMetricKey.REVENUE, "0", year=2023, evidence_id=20),
            metric(FinancialMetricKey.REVENUE, "10", year=2024, evidence_id=21),
        ]
        calculation = find(calculate_financial_metrics(inputs), CalculationKey.ANNUAL_REVENUE_GROWTH,
                           year=2024, status=CalculationStatus.UNAVAILABLE)
        self.assertIn("zero", calculation.explanation.lower())

    def test_revenue_growth_rejects_different_currencies(self):
        inputs = [
            metric(FinancialMetricKey.REVENUE, "8", year=2023, evidence_id=20, currency="USD"),
            metric(FinancialMetricKey.REVENUE, "10", year=2024, evidence_id=21, currency="INR"),
        ]
        calculation = find(calculate_financial_metrics(inputs), CalculationKey.ANNUAL_REVENUE_GROWTH,
                           year=2024, status=CalculationStatus.AMBIGUOUS)
        self.assertIn("different currency", calculation.explanation)

    def test_zero_denominator_is_unavailable_without_exception(self):
        inputs = [
            metric(FinancialMetricKey.GROSS_PROFIT, "1", evidence_id=1),
            metric(FinancialMetricKey.REVENUE, "0", evidence_id=2),
        ]
        calculation = find(calculate_financial_metrics(inputs), CalculationKey.GROSS_PROFIT_MARGIN,
                           status=CalculationStatus.UNAVAILABLE)
        self.assertIn("zero", calculation.explanation.lower())

    def test_percentage_inputs_are_not_accepted_as_currency_amounts(self):
        inputs = [
            metric(FinancialMetricKey.GROSS_PROFIT, "60", evidence_id=1),
            metric(FinancialMetricKey.REVENUE, "100", evidence_id=2),
        ]
        inputs[0].normalized_unit = "percent"
        calculation = find(calculate_financial_metrics(inputs), CalculationKey.GROSS_PROFIT_MARGIN,
                           status=CalculationStatus.AMBIGUOUS)
        self.assertIn("not a currency amount", calculation.explanation)

    def test_missing_inputs_are_explicitly_unavailable(self):
        result = calculate_financial_metrics([
            metric(FinancialMetricKey.REVENUE, "100", evidence_id=1),
        ])
        calculation = find(result, CalculationKey.GROSS_PROFIT_MARGIN,
                           status=CalculationStatus.UNAVAILABLE)
        self.assertIn("gross_profit", calculation.explanation)

    def test_different_currencies_are_rejected(self):
        inputs = [
            metric(FinancialMetricKey.GROSS_PROFIT, "60", currency="USD", evidence_id=1),
            metric(FinancialMetricKey.REVENUE, "100", currency="INR", evidence_id=2),
        ]
        calculation = find(calculate_financial_metrics(inputs), CalculationKey.GROSS_PROFIT_MARGIN,
                           status=CalculationStatus.AMBIGUOUS)
        self.assertIn("different currency", calculation.explanation)
        self.assertEqual(set(calculation.source_evidence_ids), {1, 2})

    def test_ambiguous_dollar_symbols_do_not_supply_currency_compatibility(self):
        inputs = [
            metric(FinancialMetricKey.GROSS_PROFIT, "60", currency=None, symbol="$", evidence_id=1),
            metric(FinancialMetricKey.REVENUE, "100", currency=None, symbol="$", evidence_id=2),
        ]
        calculation = find(calculate_financial_metrics(inputs), CalculationKey.GROSS_PROFIT_MARGIN,
                           status=CalculationStatus.UNAVAILABLE)
        self.assertIn("ambiguous", calculation.explanation)

    def test_different_reporting_periods_are_not_combined(self):
        inputs = [
            metric(FinancialMetricKey.GROSS_PROFIT, "60", year=2024, evidence_id=1),
            metric(FinancialMetricKey.REVENUE, "100", year=2025, evidence_id=2),
        ]
        result = calculate_financial_metrics(inputs)
        calculation = find(result, CalculationKey.GROSS_PROFIT_MARGIN,
                           year=2024, status=CalculationStatus.UNAVAILABLE)
        self.assertIn("different reporting period", calculation.explanation)
        self.assertEqual(set(calculation.source_evidence_ids), {1, 2})

    def test_actual_and_forecast_inputs_are_not_combined(self):
        inputs = [
            metric(FinancialMetricKey.GROSS_PROFIT, "60", actuality="actual", evidence_id=1),
            metric(FinancialMetricKey.REVENUE, "100", actuality="forecast_or_target", evidence_id=2),
        ]
        calculation = find(calculate_financial_metrics(inputs), CalculationKey.GROSS_PROFIT_MARGIN,
                           status=CalculationStatus.AMBIGUOUS)
        self.assertIn("actual", calculation.explanation.lower())

    def test_conflicting_same_period_evidence_is_ambiguous(self):
        inputs = [
            metric(FinancialMetricKey.GROSS_PROFIT, "60", evidence_id=1),
            metric(FinancialMetricKey.REVENUE, "100", evidence_id=2),
            metric(FinancialMetricKey.REVENUE, "120", evidence_id=3),
        ]
        calculation = find(calculate_financial_metrics(inputs), CalculationKey.GROSS_PROFIT_MARGIN,
                           status=CalculationStatus.AMBIGUOUS)
        self.assertIn("conflicting", calculation.explanation.lower())
        self.assertEqual(set(calculation.source_evidence_ids), {1, 2, 3})

    def test_agreeing_duplicate_evidence_is_preserved(self):
        inputs = [
            metric(FinancialMetricKey.GROSS_PROFIT, "60", evidence_id=1),
            metric(FinancialMetricKey.REVENUE, "100", evidence_id=2),
            metric(FinancialMetricKey.REVENUE, "100.0", evidence_id=3),
        ]
        calculation = find(calculate_financial_metrics(inputs), CalculationKey.GROSS_PROFIT_MARGIN)
        self.assertEqual(calculation.value, Decimal("60.00"))
        self.assertEqual(set(calculation.source_evidence_ids), {1, 2, 3})

    def test_verification_status_is_never_upgraded(self):
        inputs = [
            metric(FinancialMetricKey.GROSS_PROFIT, "60", verified="verified", evidence_id=1),
            metric(FinancialMetricKey.REVENUE, "100", verified="unverified", evidence_id=2),
        ]
        calculation = find(calculate_financial_metrics(inputs), CalculationKey.GROSS_PROFIT_MARGIN)
        self.assertEqual(calculation.evidence_verification_status, "unverified")

    def test_all_source_provenance_is_attached_to_calculation(self):
        inputs = [
            metric(FinancialMetricKey.GROSS_PROFIT, "60", evidence_id=1),
            metric(FinancialMetricKey.REVENUE, "100", evidence_id=2),
        ]
        calculation = find(calculate_financial_metrics(inputs), CalculationKey.GROSS_PROFIT_MARGIN)
        self.assertEqual(calculation.source_evidence_ids, [1, 2])
        self.assertEqual(calculation.source_urls, ["https://example.test/evidence/1", "https://example.test/evidence/2"])
        self.assertEqual(len(calculation.supporting_excerpts), 2)
        self.assertEqual({item.metric_key for item in calculation.input_metrics}, {
            FinancialMetricKey.GROSS_PROFIT, FinancialMetricKey.REVENUE,
        })

    def test_decimal_rounding_is_explicit_and_predictable(self):
        inputs = [
            metric(FinancialMetricKey.GROSS_PROFIT, "1.005", evidence_id=1),
            metric(FinancialMetricKey.REVENUE, "100", evidence_id=2),
            metric(FinancialMetricKey.CURRENT_ASSETS, "1", evidence_id=3),
            metric(FinancialMetricKey.CURRENT_LIABILITIES, "8", evidence_id=4),
        ]
        result = calculate_financial_metrics(inputs)
        self.assertEqual(find(result, CalculationKey.GROSS_PROFIT_MARGIN).value, Decimal("1.01"))
        ratio = find(result, CalculationKey.CURRENT_RATIO)
        self.assertEqual(ratio.value, Decimal("0.1250"))
        self.assertIn("ROUND_HALF_UP", ratio.rounding)

    def test_periodless_values_are_not_combined(self):
        inputs = [
            metric(FinancialMetricKey.GROSS_PROFIT, "60", label=None, evidence_id=1),
            metric(FinancialMetricKey.REVENUE, "100", label=None, evidence_id=2),
        ]
        for item in inputs:
            item.reporting_period_label = None
            item.fiscal_year = None
        calculation = find(calculate_financial_metrics(inputs), CalculationKey.GROSS_PROFIT_MARGIN,
                           year=None, status=CalculationStatus.UNAVAILABLE)
        self.assertIn("reporting period", calculation.explanation.lower())

    def test_input_metrics_are_not_mutated(self):
        inputs = base_metrics()
        before = [item.model_dump(mode="json") for item in inputs]
        calculate_financial_metrics(inputs)
        after = [item.model_dump(mode="json") for item in inputs]
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
