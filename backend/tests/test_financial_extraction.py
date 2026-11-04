import unittest
from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace

from app.financial import (
    ExtractionStatus,
    FinancialMetricKey,
    extract_financials,
    normalize_financial_value,
)


def evidence(raw_text, *, evidence_id=41, pages=None, extracted_information=""):
    return {
        "id": evidence_id,
        "source_url": "https://example.test/investors/annual-report.pdf",
        "source_title": "Synthetic annual report",
        "source_category": "financial",
        "extracted_information": extracted_information,
        "raw_text": raw_text,
        "publication_date": datetime(2025, 4, 3),
        "retrieval_date": datetime(2025, 4, 4),
        "verification_status": "partially_verified",
        "source_metadata": {"document_type": "pdf", "page_references": pages or []},
    }


class FinancialValueNormalizationTests(unittest.TestCase):
    def test_thousands_millions_billions_and_commas(self):
        self.assertEqual(normalize_financial_value("USD 1,250 thousand").normalized_value, Decimal("1250000"))
        self.assertEqual(normalize_financial_value("$2.5 million").normalized_value, Decimal("2500000.0"))
        self.assertEqual(normalize_financial_value("3.25 billion").normalized_value, Decimal("3250000000.00"))

    def test_indian_lakh_and_crore(self):
        crore = normalize_financial_value("₹1.5 crore")
        lakh = normalize_financial_value("INR 25 lakh")
        self.assertEqual(crore.normalized_value, Decimal("15000000.0"))
        self.assertEqual(crore.currency_code, "INR")
        self.assertEqual(lakh.normalized_value, Decimal("2500000"))

    def test_negative_and_parenthetical_values(self):
        self.assertEqual(normalize_financial_value("-450,000").normalized_value, Decimal("-450000"))
        self.assertEqual(normalize_financial_value("(450,000)").normalized_value, Decimal("-450000"))
        self.assertEqual(normalize_financial_value("($1.25 million)").normalized_value, Decimal("-1250000.00"))

    def test_ambiguous_dollar_symbol_is_preserved_without_guessing_usd(self):
        value = normalize_financial_value("$500,000")
        self.assertEqual(value.currency_symbol, "$")
        self.assertIsNone(value.currency_code)

    def test_explicit_currency_and_percent_values(self):
        self.assertEqual(normalize_financial_value("EUR 2m").currency_code, "EUR")
        self.assertEqual(normalize_financial_value("CHF 2m").currency_code, "CHF")
        self.assertEqual(normalize_financial_value("2.5 million USD").currency_code, "USD")
        percent = normalize_financial_value("12.5%")
        self.assertEqual(percent.normalized_value, Decimal("12.5"))
        self.assertEqual(percent.normalized_unit, "percent")

    def test_invalid_or_ambiguous_amount_format_is_not_parsed(self):
        self.assertIsNone(normalize_financial_value("approximately $2m"))
        self.assertIsNone(normalize_financial_value("$1,25,000"))
        self.assertIsNone(normalize_financial_value("WAS 5"))


class FinancialExtractionTests(unittest.TestCase):
    def test_extracts_revenue_with_original_label_period_and_provenance(self):
        result = extract_financials([evidence("[Page 2] FY2024 reported revenue was USD 2.5 million.", pages=[2, 3])])
        revenue = result.metrics[0]
        self.assertEqual(revenue.metric_key, FinancialMetricKey.REVENUE)
        self.assertEqual(revenue.normalized_value, Decimal("2500000.0"))
        self.assertEqual(revenue.currency_code, "USD")
        self.assertEqual(revenue.fiscal_year, 2024)
        self.assertEqual(revenue.reporting_period_label, "FY2024")
        self.assertEqual(revenue.pdf_page_references, [2])
        self.assertEqual(revenue.source_evidence_id, 41)
        self.assertEqual(revenue.source_url, "https://example.test/investors/annual-report.pdf")
        self.assertEqual(revenue.evidence_verification_status, "partially_verified")
        self.assertEqual(revenue.source_category, "financial")
        self.assertEqual(revenue.source_publication_date, datetime(2025, 4, 3))
        self.assertEqual(revenue.source_retrieval_date, datetime(2025, 4, 4))
        self.assertIn("revenue was USD 2.5 million", revenue.supporting_excerpt)

    def test_extracts_expenses_and_profit_as_distinct_metrics(self):
        result = extract_financials([evidence(
            "FY2023 actual operating expenses were $400,000 and net loss was ($120,000)."
        )])
        by_key = {metric.metric_key: metric for metric in result.metrics}
        self.assertEqual(by_key[FinancialMetricKey.OPERATING_EXPENSES].normalized_value, Decimal("400000"))
        self.assertEqual(by_key[FinancialMetricKey.NET_LOSS].normalized_value, Decimal("-120000"))
        self.assertEqual(by_key[FinancialMetricKey.NET_LOSS].actuality, "actual")

    def test_supports_all_requested_income_statement_metrics(self):
        result = extract_financials([evidence(
            "Revenue was $900,000. Cost of revenue was $300,000. Gross profit was $600,000.\n"
            "Operating expenses were $400,000. Operating income was $200,000. EBITDA was $250,000.\n"
            "Net income was $150,000. Net loss was ($20,000)."
        )])
        keys = {metric.metric_key for metric in result.metrics}
        self.assertTrue({
            FinancialMetricKey.REVENUE,
            FinancialMetricKey.COST_OF_REVENUE,
            FinancialMetricKey.GROSS_PROFIT,
            FinancialMetricKey.OPERATING_EXPENSES,
            FinancialMetricKey.OPERATING_INCOME,
            FinancialMetricKey.EBITDA,
            FinancialMetricKey.NET_INCOME,
            FinancialMetricKey.NET_LOSS,
        }.issubset(keys))

    def test_extracts_balance_sheet_metrics(self):
        result = extract_financials([evidence(
            "Cash and cash equivalents: $500,000.\nCurrent assets: $900,000.\n"
            "Total assets: $1.8 million.\nCurrent liabilities: $300,000.\n"
            "Total liabilities: $700,000.\nShort-term debt: $100,000.\n"
            "Long-term debt: $200,000.\nTotal debt: $300,000.\nShareholders' equity: $1.1 million."
        )])
        keys = {metric.metric_key for metric in result.metrics}
        self.assertTrue({
            FinancialMetricKey.CASH_AND_EQUIVALENTS,
            FinancialMetricKey.CURRENT_ASSETS,
            FinancialMetricKey.TOTAL_ASSETS,
            FinancialMetricKey.CURRENT_LIABILITIES,
            FinancialMetricKey.TOTAL_LIABILITIES,
            FinancialMetricKey.SHORT_TERM_DEBT,
            FinancialMetricKey.LONG_TERM_DEBT,
            FinancialMetricKey.TOTAL_DEBT,
            FinancialMetricKey.SHAREHOLDERS_EQUITY,
        }.issubset(keys))

    def test_extracts_cash_flow_metrics_without_calculating_free_cash_flow(self):
        result = extract_financials([evidence(
            "Operating cash flow was $300,000. Investing cash flow was ($80,000). "
            "Financing cash flow was $120,000. Capital expenditure was $40,000. "
            "Free cash flow was $260,000."
        )])
        by_key = {metric.metric_key: metric for metric in result.metrics}
        self.assertEqual(by_key[FinancialMetricKey.OPERATING_CASH_FLOW].normalized_value, Decimal("300000"))
        self.assertEqual(by_key[FinancialMetricKey.INVESTING_CASH_FLOW].normalized_value, Decimal("-80000"))
        self.assertEqual(by_key[FinancialMetricKey.FINANCING_CASH_FLOW].normalized_value, Decimal("120000"))
        self.assertEqual(by_key[FinancialMetricKey.CAPITAL_EXPENDITURE].normalized_value, Decimal("40000"))
        self.assertEqual(by_key[FinancialMetricKey.FREE_CASH_FLOW].normalized_value, Decimal("260000"))

    def test_extracts_explicit_funding_facts(self):
        result = extract_financials([evidence(
            "On March 12, 2024, the company raised a $5 million Series A round led by Acme Capital."
        )])
        by_key = {metric.metric_key: metric for metric in result.metrics}
        self.assertEqual(by_key[FinancialMetricKey.FUNDING_RAISED].normalized_value, Decimal("5000000"))
        self.assertEqual(by_key[FinancialMetricKey.FUNDING_ROUND].text_value, "Series A round")
        self.assertEqual(by_key[FinancialMetricKey.FUNDING_STAGE].text_value, "Series A")
        self.assertEqual(by_key[FinancialMetricKey.FUNDING_DATE].date_value, date(2024, 3, 12))
        self.assertEqual(by_key[FinancialMetricKey.NAMED_INVESTORS].text_value, "Acme Capital")

    def test_preserves_multiple_periods_instead_of_merging(self):
        result = extract_financials([evidence(
            "FY2023 reported revenue was $1 million. FY2024 reported revenue was $2 million."
        )])
        revenues = [metric for metric in result.metrics if metric.metric_key == FinancialMetricKey.REVENUE]
        self.assertEqual([(item.fiscal_year, item.normalized_value) for item in revenues], [
            (2023, Decimal("1000000")), (2024, Decimal("2000000")),
        ])

    def test_identifies_quarter_and_forecast_separately_from_actuals(self):
        result = extract_financials([evidence(
            "Q1 FY2024 actual revenue was $2 million. Q1 FY2025 forecast revenue is $3 million."
        )])
        revenues = [metric for metric in result.metrics if metric.metric_key == FinancialMetricKey.REVENUE]
        self.assertEqual(revenues[0].fiscal_quarter, 1)
        self.assertEqual(revenues[0].actuality, "actual")
        self.assertEqual(revenues[1].fiscal_year, 2025)
        self.assertEqual(revenues[1].actuality, "forecast_or_target")

    def test_period_end_date_is_retained_when_explicit(self):
        result = extract_financials([evidence(
            "Revenue for the year ended December 31, 2024 was $4 million."
        )])
        self.assertEqual(result.metrics[0].period_end_date, date(2024, 12, 31))

    def test_period_start_and_end_dates_are_retained_when_explicit(self):
        result = extract_financials([evidence(
            "Revenue from January 1, 2024 to December 31, 2024 was $4 million."
        )])
        self.assertEqual(result.metrics[0].period_start_date, date(2024, 1, 1))
        self.assertEqual(result.metrics[0].period_end_date, date(2024, 12, 31))

    def test_partial_funding_date_does_not_invent_a_day(self):
        result = extract_financials([evidence("The seed funding round closed in March 2024.")])
        funding_date = next(metric for metric in result.metrics if metric.metric_key == FinancialMetricKey.FUNDING_DATE)
        self.assertIsNone(funding_date.date_value)
        self.assertEqual(funding_date.text_value, "March 2024")

    def test_ignores_arr_when_it_is_not_recognized_revenue(self):
        result = extract_financials([evidence("ARR was $4 million; recognized revenue was $1 million.")])
        revenues = [metric for metric in result.metrics if metric.metric_key == FinancialMetricKey.REVENUE]
        self.assertEqual(len(revenues), 1)
        self.assertEqual(revenues[0].normalized_value, Decimal("1000000"))

    def test_funding_amount_is_not_misclassified_as_revenue(self):
        result = extract_financials([evidence("The company raised $3 million in a Series A round.")])
        self.assertEqual([metric.metric_key for metric in result.metrics].count(FinancialMetricKey.FUNDING_RAISED), 1)
        self.assertFalse(any(metric.metric_key == FinancialMetricKey.REVENUE for metric in result.metrics))

    def test_missing_data_returns_no_fabricated_metrics(self):
        result = extract_financials([evidence("The company serves 12,000 customers and plans to expand next year.")])
        self.assertEqual(result.metrics, [])
        self.assertEqual(result.unresolved, [])
        self.assertIn(FinancialMetricKey.REVENUE, result.missing_metrics)

    def test_ambiguous_multiple_amounts_are_reported_unresolved(self):
        result = extract_financials([evidence("Revenue grew from $1 million to $2 million during the year.")])
        self.assertEqual(result.metrics, [])
        self.assertEqual(result.unresolved[0].metric_key, FinancialMetricKey.REVENUE)
        self.assertEqual(result.unresolved[0].extraction_status, ExtractionStatus.AMBIGUOUS)

    def test_unsupported_number_is_not_attached_to_nearby_metric(self):
        result = extract_financials([evidence("Revenue outlook remains strong; 20 new markets were entered.")])
        self.assertEqual(result.metrics, [])

    def test_unsupported_scale_is_returned_as_unresolved(self):
        result = extract_financials([evidence("Revenue was $5 quadrillion in FY2024.")])
        self.assertEqual(result.metrics, [])
        self.assertEqual(result.unresolved[0].metric_key, FinancialMetricKey.REVENUE)
        self.assertEqual(result.unresolved[0].evidence_verification_status, "partially_verified")
        self.assertEqual(result.unresolved[0].extraction_status, ExtractionStatus.UNRESOLVED)

    def test_reads_orm_like_evidence_records(self):
        record = SimpleNamespace(**evidence("Revenue was INR 25 lakh."))
        result = extract_financials([record])
        self.assertEqual(result.metrics[0].normalized_value, Decimal("2500000"))
        self.assertEqual(result.metrics[0].currency_code, "INR")

    def test_summary_text_is_only_used_when_raw_text_is_missing(self):
        result = extract_financials([evidence(
            "Revenue was $2 million.", extracted_information="Revenue was $9 million."
        )])
        self.assertEqual(len(result.metrics), 1)
        self.assertEqual(result.metrics[0].normalized_value, Decimal("2000000"))


if __name__ == "__main__":
    unittest.main()
