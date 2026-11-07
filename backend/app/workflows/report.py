from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fpdf import FPDF

from app.db.models import Analysis, Startup

_RISK_ORDER = {
    "UNKNOWN": 0,
    "LOW": 1,
    "MEDIUM": 2,
    "HIGH": 3,
    "CRITICAL": 4,
}

_AGENT_NAMES = {
    "financial": "Financial Agent",
    "marketing": "Marketing Agent",
    "legal": "Legal Agent",
}

_SECTION_TITLES = [
    "Executive Investment Summary",
    "Company Profile",
    "Investment Opportunity Analysis",
    "Financial Due Diligence",
    "Market and Marketing Analysis",
    "Legal and Compliance Analysis",
    "Risk Assessment",
    "Verification and Cross-Analysis",
    "Information Gaps",
    "Investor Questions",
    "Investment Considerations",
    "Final Assessment",
]


def generate_final_report(
    analysis: Analysis,
    startup: Startup,
    specialist_outputs: Dict[str, Any],
    specialist_errors: Dict[str, Any],
    verification: Optional[Dict[str, Any]] = None,
    aggregation: Optional[Dict[str, Any]] = None,
    workflow_id: Optional[int] = None,
) -> Dict[str, Any]:
    outputs = _outputs(specialist_outputs)
    overall_risk = _overall_risk(outputs, aggregation)
    verification_status = _verification_status(verification)
    failed_agents = sorted(specialist_errors)
    missing_information = _missing_information(outputs, specialist_errors)
    all_findings = _all_findings(outputs)
    evidence_references = _all_evidence_references(outputs, verification)
    contradictions = _contradictions(verification)
    source_reliability = _source_reliability(verification)

    final_category = _final_category(
        overall_risk,
        verification_status,
        failed_agents,
        contradictions,
        missing_information,
        all_findings,
    )

    sections = [
        _executive_section(
            analysis, overall_risk, verification_status, outputs, failed_agents, all_findings
        ),
        _action_section(
            analysis, overall_risk, missing_information, all_findings, contradictions, verification_status
        ),
        _scorecard_section(outputs, verification, source_reliability, overall_risk),
        _positives_section(all_findings, outputs),
        _risks_section(all_findings, outputs),
        _agent_analysis_section(analysis, outputs, verification, all_findings),
        _missing_section(missing_information, all_findings, failed_agents),
        _evidence_section(evidence_references, verification),
        _final_guidance_section(
            analysis, overall_risk, verification_status, final_category, missing_information, all_findings
        ),
    ]

    generated_at = datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z"

    key_positive_indicators = sorted(
        {
            finding.get("dimension")
            for finding in all_findings
            if str(finding.get("risk_level", "")).upper() == "LOW"
            and finding.get("dimension")
        }
    )
    major_concerns = sorted(
        {
            finding.get("dimension")
            for finding in all_findings
            if str(finding.get("risk_level", "")).upper() in {"HIGH", "CRITICAL"}
            and finding.get("dimension")
        }
    )

    return {
        "title": f"{analysis.startup_name} Investor Due Diligence Report",
        "generated_at": generated_at,
        "report_id": workflow_id,
        "analysis_id": analysis.id,
        "workflow_id": workflow_id,
        "startup_id": startup.id,
        "company": {
            "analysis_id": analysis.id,
            "startup_id": startup.id,
            "name": analysis.startup_name,
            "website": analysis.website,
            "industry": analysis.industry or "Not provided",
            "country": analysis.country or "Not provided",
            "additional_information": analysis.additional_information or "Not provided",
            "analysis_status": analysis.status,
            "overall_assessment": analysis.overall_assessment,
        },
        "overall_risk": overall_risk,
        "overall_assessment": _assessment(overall_risk),
        "final_assessment_category": final_category,
        "evidence_status": (
            aggregation.get("evidence_status")
            if aggregation
            else _overall_evidence_status(outputs)
        ),
        "verification_status": verification_status,
        "recommendation": _recommendation(overall_risk, final_category),
        "key_positive_indicators": key_positive_indicators,
        "major_concerns": major_concerns,
        "executive_summary": _executive_summary_text(
            analysis.startup_name,
            overall_risk,
            verification_status,
            len(outputs),
            failed_agents,
            all_findings,
            missing_information,
        ),
        "executive_summary_section": sections[0],
        "company_profile": {
            "analysis_id": analysis.id,
            "startup_id": startup.id,
            "name": analysis.startup_name,
            "website": analysis.website,
            "industry": analysis.industry or "Not provided",
            "country": analysis.country or "Not provided",
            "additional_information": analysis.additional_information or "Not provided",
            "analysis_status": analysis.status,
            "overall_assessment": analysis.overall_assessment,
        },
        "investment_opportunity": sections[1],
        "financial_due_diligence": sections[5],
        "market_analysis": sections[5],
        "legal_analysis": sections[5],
        "risk_assessment": sections[4],
        "verification": sections[7],
        "information_gaps": sections[6],
        "investor_questions": _investor_questions_section(
            missing_information, all_findings, contradictions, verification_status
        )["questions"],
        "investment_considerations": sections[1],
        "final_assessment": sections[-1],
        "specialist_reports": _specialist_reports(outputs),
        "verification_summary": _verification_summary(verification),
        "failed_agents": failed_agents,
        "missing_information": missing_information,
        "contradictions": contradictions,
        "source_reliability": source_reliability,
        "evidence_references": evidence_references,
        "sections": sections,
        "charts": _report_charts(all_findings, source_reliability, verification),
        "disclaimer": (
            "This report is based solely on retrieved public evidence and specialist "
            "agent analysis. It is not independent verification, legal advice, an "
            "audit, or a recommendation to invest. Missing information is explicitly "
            "marked as unavailable rather than estimated."
        ),
    }


def generate_report_pdf(
    report: Dict[str, Any],
    analysis: Optional[Analysis] = None,
    startup: Optional[Startup] = None,
) -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_title(_pdf_text(report.get("title", "Due Diligence Report")))
    pdf.set_author("Ventrix")

    pdf.set_font("Helvetica", "B", 18)
    pdf.multi_cell(0, 10, _pdf_text(report.get("title", "Due Diligence Report")))
    pdf.ln(2)

    pdf.set_font("Helvetica", "", 10)
    metadata = [
        ("Startup", report.get("company", {}).get("name", "Not provided")),
        ("Website", report.get("company", {}).get("website", "Not provided")),
        ("Industry", report.get("company", {}).get("industry", "Not provided")),
        ("Analysis ID", str(report.get("analysis_id", "Not provided"))),
        ("Report ID", str(report.get("report_id", "Not provided"))),
        ("Generated", str(report.get("generated_at", "Not provided"))),
        ("Overall risk", str(report.get("overall_risk", "UNKNOWN"))),
        ("Final assessment", str(report.get("final_assessment_category", "Not provided"))),
    ]
    for label, value in metadata:
        pdf.set_font("Helvetica", "B", 10)
        pdf.write(5, _pdf_text(f"{label}: "))
        pdf.set_font("Helvetica", "", 10)
        pdf.write(5, _pdf_text(value))
        pdf.ln(5)

    pdf.ln(3)
    for section in report.get("sections", []):
        pdf.set_font("Helvetica", "B", 13)
        pdf.multi_cell(0, 8, _pdf_text(section.get("title", "Section")))
        pdf.ln(1)

        for paragraph in section.get("content", []):
            pdf.set_font("Helvetica", "", 10)
            pdf.multi_cell(0, 5, _pdf_text(paragraph))
            pdf.ln(2)

        for table in section.get("tables", []):
            _pdf_table(pdf, table)

        for indicator in section.get("risk_indicators", []):
            pdf.set_font("Helvetica", "B", 10)
            pdf.write(5, _pdf_text(f"{indicator.get('label', 'Risk')}: "))
            pdf.set_font("Helvetica", "", 10)
            pdf.write(5, _pdf_text(f"{indicator.get('level', 'UNKNOWN')} - {indicator.get('reason', '')}"))
            pdf.ln(5)

        refs = section.get("evidence_references", [])
        if refs:
            pdf.set_font("Helvetica", "B", 10)
            pdf.write(5, "Evidence references: ")
            pdf.set_font("Helvetica", "", 9)
            pdf.multi_cell(
                0,
                5,
                _pdf_text(
                    ", ".join(
                        f"{ref.get('evidence_id')} ({ref.get('verification_status', 'UNVERIFIED')})"
                        for ref in refs
                    )
                ),
            )
            pdf.ln(2)

        pdf.ln(2)

    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", "B", 11)
    pdf.multi_cell(0, 7, "Disclaimer")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(0, 5, _pdf_text(report.get("disclaimer", "")))
    pdf_output = pdf.output()

    if isinstance(pdf_output, str):
        return pdf_output.encode("latin-1")

    return bytes(pdf_output)


def _pdf_text(value: Any) -> str:
    return str(value).encode("latin-1", "replace").decode("latin-1")


def _pdf_table(pdf: FPDF, table: Dict[str, Any]) -> None:
    columns = table.get("columns", [])
    rows = table.get("rows", [])
    if not columns or not rows:
        return

    pdf.set_font("Helvetica", "B", 9)
    widths = [190 / len(columns)] * len(columns)
    for column in columns:
        pdf.cell(widths[0], 6, _pdf_text(str(column)[:40]), border=1)
    pdf.ln()
    pdf.set_font("Helvetica", "", 8)
    for row in rows[:25]:
        for index, value in enumerate(row):
            pdf.cell(widths[index % len(widths)], 6, _pdf_text(str(value)[:45]), border=1)
        pdf.ln()
    pdf.ln(2)


def _outputs(specialist_outputs: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    outputs = {}
    for key, output in (specialist_outputs or {}).items():
        if hasattr(output, "model_dump"):
            outputs[key] = output.model_dump(mode="json")
        elif isinstance(output, dict):
            outputs[key] = output
    return outputs


def _overall_risk(
    outputs: Dict[str, Dict[str, Any]],
    aggregation: Optional[Dict[str, Any]],
) -> str:
    if aggregation and aggregation.get("overall_risk"):
        return str(aggregation["overall_risk"])

    risks = [
        str(output.get("risk_level", "UNKNOWN")).upper()
        for output in outputs.values()
    ]
    known = [risk for risk in risks if risk in _RISK_ORDER and risk != "UNKNOWN"]
    if not known:
        return "UNKNOWN"
    return max(known, key=lambda risk: _RISK_ORDER[risk])


def _overall_evidence_status(outputs: Dict[str, Dict[str, Any]]) -> str:
    statuses = [
        str(output.get("evidence_status", "UNAVAILABLE"))
        for output in outputs.values()
    ]
    if not statuses:
        return "UNAVAILABLE"
    if all(status == "VERIFIED" for status in statuses):
        return "VERIFIED"
    if any(status in {"VERIFIED", "PARTIALLY_VERIFIED"} for status in statuses):
        return "PARTIALLY_VERIFIED"
    if any(status == "UNVERIFIED" for status in statuses):
        return "UNVERIFIED"
    return "UNAVAILABLE"


def _verification_status(verification: Optional[Dict[str, Any]]) -> str:
    if not verification:
        return "UNAVAILABLE"
    return str(
        verification.get("verification_status")
        or verification.get("status")
        or "UNAVAILABLE"
    ).upper()


def _missing_information(
    outputs: Dict[str, Dict[str, Any]],
    specialist_errors: Dict[str, Any],
) -> List[str]:
    missing = []
    seen = set()
    for output in outputs.values():
        for item in output.get("missing_information", []) or []:
            if item in seen:
                continue
            seen.add(item)
            missing.append(item)
    for agent_key, error in specialist_errors.items():
        item = f"{_AGENT_NAMES.get(agent_key, agent_key)} failed: {error}"
        if item not in seen:
            seen.add(item)
            missing.append(item)
    for output in outputs.values():
        for finding in output.get("findings", []) or []:
            if not isinstance(finding, dict):
                continue
            if finding.get("evidence_status") == "UNAVAILABLE":
                item = (
                    f"{finding.get('dimension', 'Unknown dimension')}: "
                    "no supporting evidence was found."
                )
                if item not in seen:
                    seen.add(item)
                    missing.append(item)
    # Keep the report concise and readable for end users.
    return missing[:15]


def _all_findings(outputs: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    findings = []
    for agent_key, output in outputs.items():
        for finding in output.get("findings", []) or []:
            if not isinstance(finding, dict):
                continue
            item = dict(finding)
            item["agent_key"] = agent_key
            item["agent_name"] = output.get("agent_name", _AGENT_NAMES.get(agent_key))
            item["summary"] = _truncate(item.get("summary"), 90)
            item["explanation"] = _truncate(item.get("explanation"), 150)
            item["investor_impact"] = _truncate(item.get("investor_impact"), 110)
            findings.append(item)
    return findings


def _all_evidence_references(
    outputs: Dict[str, Dict[str, Any]],
    verification: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    references = []
    seen = set()
    for output in outputs.values():
        for reference in output.get("evidence_references", []) or []:
            if not isinstance(reference, dict):
                continue
            evidence_id = reference.get("evidence_id")
            if evidence_id in seen:
                continue
            seen.add(evidence_id)
            references.append(reference)
    if verification:
        for reference in verification.get("supporting_evidence", []) or []:
            if not isinstance(reference, dict):
                continue
            evidence_id = reference.get("evidence_id")
            if evidence_id in seen:
                continue
            seen.add(evidence_id)
            references.append(reference)
    return references


def _contradictions(verification: Optional[Dict[str, Any]]) -> List[Any]:
    if not verification:
        return []
    return list(verification.get("contradictions", []) or [])


def _source_reliability(verification: Optional[Dict[str, Any]]) -> List[Any]:
    if not verification:
        return []
    return list(verification.get("source_reliability", []) or [])


def _assessment(overall_risk: str) -> str:
    return {
        "CRITICAL": "Critical risk",
        "HIGH": "High risk",
        "MEDIUM": "Moderate risk",
        "LOW": "Low risk",
        "UNKNOWN": "Insufficient Information",
    }.get(overall_risk, "Insufficient Information")


def _recommendation(overall_risk: str, final_category: str) -> str:
    if final_category == "Do Not Proceed" or overall_risk in {"CRITICAL", "HIGH"}:
        return "High Risk — Exercise Caution"
    if final_category == "Hold / Further Investigation Required":
        return "Potential Investment — Requires Validation"
    if final_category == "Proceed Conditionally":
        return "Potential Investment — Requires Validation"
    if final_category == "Proceed to Next Stage":
        return "Proceed with Further Due Diligence"
    if overall_risk == "UNKNOWN":
        return "Insufficient Information for Assessment"
    return "Proceed with Further Due Diligence"


def _final_category(
    overall_risk: str,
    verification_status: str,
    failed_agents: List[str],
    contradictions: List[Any],
    missing_information: List[str],
    all_findings: List[Dict[str, Any]],
) -> str:
    if overall_risk == "CRITICAL":
        return "Do Not Proceed"
    if (
        overall_risk == "HIGH"
        or contradictions
        or failed_agents
        or verification_status in {"CONTRADICTED", "UNAVAILABLE"}
    ):
        return "Hold / Further Investigation Required"
    if (
        overall_risk in {"MEDIUM", "UNKNOWN"}
        or verification_status in {"PARTIALLY_VERIFIED", "UNVERIFIED"}
        or any("no supporting evidence" in item.lower() for item in missing_information)
    ):
        return "Proceed Conditionally"
    if overall_risk == "LOW" and verification_status == "VERIFIED":
        return "Proceed to Next Stage"
    return "Proceed Conditionally"


def _executive_summary_text(
    name: str,
    overall_risk: str,
    verification_status: str,
    output_count: int,
    failed_agents: List[str],
    all_findings: List[Dict[str, Any]],
    missing_information: List[str],
) -> str:
    high_risk = [
        finding.get("dimension", "Unknown")
        for finding in all_findings
        if str(finding.get("risk_level", "")).upper() in {"HIGH", "CRITICAL"}
    ]
    summary = (
        f"{name} was reviewed using {output_count} specialist report(s). "
        f"Overall risk: {overall_risk.lower()}. "
        f"Verification: {verification_status.lower().replace('_', ' ')}. "
        f"Missing information items: {len(missing_information)}."
    )
    if high_risk:
        summary += (
            " Key risk areas: " + ", ".join(sorted(set(high_risk))) + "."
        )
    if failed_agents:
        summary += (
            " Failed agents: " + ", ".join(failed_agents) + "."
        )
    summary += (
        " This is not an investment recommendation."
    )
    return summary


def _section_base(title: str, content: List[str]) -> Dict[str, Any]:
    return {
        "title": title,
        "content": content,
        "findings": [],
        "evidence_references": [],
        "tables": [],
        "charts": [],
        "risk_indicators": [],
        "verification_status": None,
    }


def _executive_section(
    analysis: Analysis,
    overall_risk: str,
    verification_status: str,
    outputs: Dict[str, Dict[str, Any]],
    failed_agents: List[str],
    all_findings: List[Dict[str, Any]],
) -> Dict[str, Any]:
    section = _section_base("Executive Investment Summary", [
        (
            f"This report assesses {analysis.startup_name} from an investor's "
            f"perspective using retrieved public evidence, structured specialist "
            f"agent analysis, and cross-verification. The company operates in "
            f"{analysis.industry or 'an unspecified industry'} and its website is "
            f"{analysis.website}."
        ),
        (
            f"The aggregate evidence-backed risk level is {overall_risk.lower()}. "
            f"Verification of specialist claims against stored evidence resulted in "
            f"{verification_status.lower().replace('_', ' ')} status. "
            f"{len(outputs)} of 3 specialist agents produced completed reports."
        ),
        (
            "The assessment below is limited to retrieved public evidence. Missing "
            "information is reported as unavailable rather than estimated, and no "
            "numerical investment score has been generated."
        ),
    ])
    section["risk_indicators"] = [
        {
            "label": "Overall risk",
            "level": overall_risk,
            "reason": "Highest risk level among completed specialist findings.",
        },
        {
            "label": "Evidence verification",
            "level": verification_status,
            "reason": "Cross-check of specialist claims against stored evidence.",
        },
    ]
    section["findings"] = [
        {
            "dimension": finding.get("dimension"),
            "summary": finding.get("summary"),
            "risk_level": finding.get("risk_level"),
            "evidence_status": finding.get("evidence_status"),
            "agent": finding.get("agent_name"),
        }
        for finding in all_findings
        if str(finding.get("risk_level", "")).upper() in {"HIGH", "CRITICAL"}
    ]
    section["verification_status"] = verification_status
    return section


def _company_profile_section(
    analysis: Analysis,
    startup: Startup,
    outputs: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    section = _section_base("Company Profile", [
        (
            f"Company name: {analysis.startup_name}. Website: {analysis.website}. "
            f"Industry: {analysis.industry or 'Not provided'}. Country: "
            f"{analysis.country or 'Not provided'}."
        ),
        (
            f"Additional submitted information: "
            f"{analysis.additional_information or 'Not provided'}."
        ),
        (
            "The profile below reflects submitted analysis data and retrieved public "
            "evidence. Fields not present in the evidence are marked as unavailable."
        ),
    ])
    section["profile"] = {
        "analysis_id": analysis.id,
        "startup_id": startup.id,
        "name": analysis.startup_name,
        "website": analysis.website,
        "industry": analysis.industry or "Not provided",
        "country": analysis.country or "Not provided",
        "additional_information": analysis.additional_information or "Not provided",
        "analysis_status": analysis.status,
        "overall_assessment": analysis.overall_assessment,
        "retrieved_evidence_sources": len(
            {
                reference.get("evidence_id")
                for output in outputs.values()
                for reference in output.get("evidence_references", []) or []
                if isinstance(reference, dict)
            }
        ),
    }
    section["tables"] = [
        {
            "title": "Company profile",
            "columns": ["Field", "Value"],
            "rows": [
                ["Name", analysis.startup_name],
                ["Website", analysis.website],
                ["Industry", analysis.industry or "Not provided"],
                ["Country", analysis.country or "Not provided"],
                ["Analysis status", analysis.status],
                ["Overall assessment", analysis.overall_assessment or "Not provided"],
            ],
        }
    ]
    section["verification_status"] = None
    return section


def _investment_opportunity_section(
    analysis: Analysis,
    outputs: Dict[str, Dict[str, Any]],
    overall_risk: str,
) -> Dict[str, Any]:
    marketing = outputs.get("marketing", {})
    financial = outputs.get("financial", {})
    legal = outputs.get("legal", {})
    content = [
        (
            f"The investment opportunity is assessed from market, financial, and legal "
            f"perspectives. The current aggregate risk level is {overall_risk.lower()}."
        ),
        _agent_paragraph(marketing, "Market evidence"),
        _agent_paragraph(financial, "Financial evidence"),
        _agent_paragraph(legal, "Legal evidence"),
        (
            "Opportunity quality depends on the strength of the retrieved evidence. "
            "Claims without supporting evidence are treated as unverified or unavailable."
        ),
    ]
    section = _section_base("Investment Opportunity Analysis", content)
    section["tables"] = [
        {
            "title": "Specialist coverage",
            "columns": ["Agent", "Risk level", "Evidence status", "Execution status"],
            "rows": [
                [
                    output.get("agent_name", _AGENT_NAMES.get(key, key)),
                    output.get("risk_level", "UNKNOWN"),
                    output.get("evidence_status", "UNAVAILABLE"),
                    output.get("execution_status", "UNKNOWN"),
                ]
                for key, output in outputs.items()
            ],
        }
    ]
    section["verification_status"] = None
    return section


def _agent_paragraph(output: Dict[str, Any], label: str) -> str:
    if not output:
        return f"{label}: no completed specialist report is available."
    findings = output.get("findings", []) or []
    supported = [
        finding.get("dimension")
        for finding in findings
        if isinstance(finding, dict)
        and finding.get("evidence_status") in {"VERIFIED", "PARTIALLY_VERIFIED"}
    ]
    if supported:
        return (
            f"{label}: supported dimensions include {', '.join(supported[:6])}. "
            f"Overall status is {output.get('evidence_status', 'UNAVAILABLE')}."
        )
    return (
        f"{label}: no supported dimensions were identified in the retrieved evidence. "
        f"Overall status is {output.get('evidence_status', 'UNAVAILABLE')}."
    )


def _specialist_section(
    title: str,
    agent_key: str,
    outputs: Dict[str, Dict[str, Any]],
    caveat: str,
) -> Dict[str, Any]:
    output = outputs.get(agent_key, {})
    findings = [
        finding
        for finding in (output.get("findings", []) if isinstance(output, dict) else [])
        if isinstance(finding, dict)
    ]
    content = [
        (
            f"{_AGENT_NAMES.get(agent_key, agent_key)} assessed this area using retrieved "
            f"public evidence only. {caveat}"
        ),
        (
            f"Overall risk: {output.get('risk_level', 'UNKNOWN')}. "
            f"Evidence status: {output.get('evidence_status', 'UNAVAILABLE')}. "
            f"Execution status: {output.get('execution_status', 'UNKNOWN')}."
        ),
        (
            output.get("investor_impact")
            or "No investor impact summary is available."
        ),
    ]
    if output.get("missing_information"):
        content.append(
            "Missing information: "
            + "; ".join(output.get("missing_information", []))
            + "."
        )

    section = _section_base(title, content)
    simplified_findings = []
    for finding in findings:
        if str(finding.get("evidence_status", "")).upper() == "UNAVAILABLE":
            summary = "No public evidence was found for this area."
            explanation = (
                "The retrieved public sources do not support this dimension. "
                "This is an information gap, not proof that the risk is absent."
            )
            investor_impact = "Request supporting documents before relying on this area."
        else:
            summary = _truncate(finding.get("summary"), 90)
            explanation = _truncate(finding.get("explanation"), 150)
            investor_impact = _truncate(finding.get("investor_impact"), 110)
        simplified_findings.append(
            {
                "dimension": finding.get("dimension"),
                "summary": summary,
                "explanation": explanation,
                "risk_level": finding.get("risk_level"),
                "evidence_status": finding.get("evidence_status"),
                "investor_impact": investor_impact,
                "evidence_references": finding.get("evidence_references", []),
            }
        )
    section["findings"] = simplified_findings
    section["evidence_references"] = [
        reference
        for reference in (output.get("evidence_references", []) if isinstance(output, dict) else [])
        if isinstance(reference, dict)
    ]
    section["tables"] = [
        {
            "title": f"{_AGENT_NAMES.get(agent_key, agent_key)} findings",
            "columns": ["Dimension", "Risk", "Evidence status", "Summary"],
            "rows": [
                [
                    finding.get("dimension", "Unknown"),
                    finding.get("risk_level", "UNKNOWN"),
                    finding.get("evidence_status", "UNAVAILABLE"),
                    _truncate(finding.get("summary", ""), 90),
                ]
                for finding in findings
            ],
        }
    ]
    section["charts"] = [_risk_distribution_chart(findings, f"{title} risk distribution")]
    section["risk_indicators"] = _risk_indicators(findings)
    section["verification_status"] = None
    section["agent_key"] = agent_key
    return section


def _risk_section(
    overall_risk: str,
    all_findings: List[Dict[str, Any]],
    outputs: Dict[str, Dict[str, Any]],
    aggregation: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    high_risk_findings = [
        finding
        for finding in all_findings
        if str(finding.get("risk_level", "")).upper() in {"HIGH", "CRITICAL", "MEDIUM"}
    ]
    content = [
        (
            f"The aggregate risk level is {overall_risk.lower()}, derived from the "
            f"highest risk level among completed specialist findings. No numerical "
            f"investment score has been generated."
        ),
        (
            "Risk indicators distinguish verified, partially verified, unverified, "
            "and unavailable evidence. A risk finding is only as strong as its "
            "underlying evidence."
        ),
    ]
    if aggregation:
        content.append(
            f"Aggregation summary: {aggregation.get('specialist_count', 0)} specialist "
            f"report(s) completed, {len(aggregation.get('failed_agents', []))} failed, "
            f"and {len(aggregation.get('missing_information', []))} missing-information "
            f"item(s) were recorded."
        )

    section = _section_base("Risk Assessment", content)
    section["findings"] = [
        {
            "dimension": finding.get("dimension"),
            "summary": finding.get("summary"),
            "risk_level": finding.get("risk_level"),
            "evidence_status": finding.get("evidence_status"),
            "agent": finding.get("agent_name"),
            "investor_impact": finding.get("investor_impact"),
        }
        for finding in high_risk_findings
    ]
    section["tables"] = [
        {
            "title": "Risk findings",
            "columns": ["Agent", "Dimension", "Risk", "Evidence status"],
            "rows": [
                [
                    finding.get("agent_name", "Unknown"),
                    finding.get("dimension", "Unknown"),
                    finding.get("risk_level", "UNKNOWN"),
                    finding.get("evidence_status", "UNAVAILABLE"),
                ]
                for finding in high_risk_findings
            ],
        }
    ]
    section["charts"] = [
        _risk_distribution_chart(all_findings, "Overall risk distribution")
    ]
    section["risk_indicators"] = _risk_indicators(all_findings)
    section["verification_status"] = None
    return section


def _verification_section(
    verification: Optional[Dict[str, Any]],
    verification_status: str,
    contradictions: List[Any],
    source_reliability: List[Any],
) -> Dict[str, Any]:
    if verification:
        content = [
            (
                f"Verification status: {verification_status.lower().replace('_', ' ')}. "
                f"{verification.get('total_findings', 0)} claim(s) were reviewed, "
                f"{verification.get('valid_references', 0)} of "
                f"{verification.get('checked_references', 0)} evidence references were "
                f"valid, and {verification.get('invalid_references', 0)} were invalid."
            ),
            (
                "The Verification Agent did not blindly accept specialist outputs. "
                "Claims were checked against stored evidence, including verification "
                "status, missing references, unsupported claims, and contradictions."
            ),
        ]
        if verification.get("detailed_reasoning"):
            content.append(str(verification.get("detailed_reasoning")))
        if verification.get("investor_impact"):
            content.append(str(verification.get("investor_impact")))
    else:
        content = [
            "No verification output is available. Specialist claims have not been "
            "cross-checked against stored evidence."
        ]

    section = _section_base("Verification and Cross-Analysis", content)
    section["findings"] = [
        {
            "dimension": "Verification",
            "summary": issue,
            "risk_level": "MEDIUM",
            "evidence_status": verification_status,
        }
        for issue in (verification.get("issues", []) if verification else [])
    ]
    section["tables"] = []
    if verification:
        section["tables"].append(
            {
                "title": "Verification metrics",
                "columns": ["Metric", "Value"],
                "rows": [
                    ["Claims reviewed", verification.get("total_findings", 0)],
                    ["Checked references", verification.get("checked_references", 0)],
                    ["Valid references", verification.get("valid_references", 0)],
                    ["Invalid references", verification.get("invalid_references", 0)],
                    ["Unsupported claims", len(verification.get("unsupported_claims", []) or [])],
                    ["Contradictions", len(contradictions)],
                ],
            }
        )
        if source_reliability:
            section["tables"].append(
                {
                    "title": "Source reliability",
                    "columns": ["Evidence ID", "Status", "Reliability", "Score"],
                    "rows": [
                        [
                            item.get("evidence_id", "Unknown"),
                            item.get("verification_status", "UNKNOWN"),
                            item.get("reliability_level", "UNKNOWN"),
                            item.get("reliability_score", 0),
                        ]
                        for item in source_reliability
                        if isinstance(item, dict)
                    ],
                }
            )
    section["charts"] = [
        _verification_chart(verification, verification_status)
    ] if verification else []
    section["risk_indicators"] = [
        {
            "label": "Verification status",
            "level": verification_status,
            "reason": "Cross-analysis of specialist claims against stored evidence.",
        }
    ]
    for contradiction in contradictions:
        section["risk_indicators"].append(
            {
                "label": "Contradiction",
                "level": "HIGH",
                "reason": str(contradiction.get("reasoning") if isinstance(contradiction, dict) else contradiction),
            }
        )
    section["verification_status"] = verification_status
    return section


def _information_gaps_section(
    missing_information: List[str],
    all_findings: List[Dict[str, Any]],
    failed_agents: List[str],
) -> Dict[str, Any]:
    unavailable = [
        finding
        for finding in all_findings
        if finding.get("evidence_status") == "UNAVAILABLE"
    ]
    content = [
        (
            "The following information is unavailable or unverified. These gaps are "
            "reported explicitly and have not been estimated."
        )
    ]
    if not missing_information and not unavailable and not failed_agents:
        content.append("No information gaps were identified in the retrieved evidence set.")
    else:
        content.append(
            "Information gaps reduce the reliability of the analysis and should be "
            "resolved before an investment decision."
        )

    section = _section_base("Information Gaps", content)
    section["findings"] = [
        {
            "dimension": finding.get("dimension"),
            "summary": finding.get("summary"),
            "risk_level": "UNKNOWN",
            "evidence_status": "UNAVAILABLE",
            "agent": finding.get("agent_name"),
        }
        for finding in unavailable
    ]
    section["tables"] = [
        {
            "title": "Missing information",
            "columns": ["Gap"],
            "rows": [[item] for item in missing_information],
        }
    ]
    if failed_agents:
        section["tables"].append(
            {
                "title": "Failed specialist agents",
                "columns": ["Agent"],
                "rows": [[agent] for agent in failed_agents],
            }
        )
    section["verification_status"] = None
    return section


def _investor_questions_section(
    missing_information: List[str],
    all_findings: List[Dict[str, Any]],
    contradictions: List[Any],
    verification_status: str,
) -> Dict[str, Any]:
    questions = []
    seen = set()

    def add(question: str) -> None:
        if question not in seen:
            seen.add(question)
            questions.append(question)

    for item in missing_information:
        add(f"Can the company provide primary documentation for: {item}?")

    for finding in all_findings:
        if str(finding.get("risk_level", "")).upper() in {"HIGH", "CRITICAL"}:
            add(
                f"How does the company mitigate the risk identified in "
                f"{finding.get('dimension', 'this area')}?"
            )
        if finding.get("evidence_status") in {"UNVERIFIED", "PARTIALLY_VERIFIED"}:
            add(
                f"Can the {finding.get('agent_name', 'specialist')} finding on "
                f"{finding.get('dimension', 'this area')} be independently verified?"
            )

    for contradiction in contradictions:
        add("How should the conflicting specialist findings be reconciled?")

    if verification_status in {"UNVERIFIED", "UNAVAILABLE"}:
        add("What additional evidence can be provided to support the specialist claims?")

    if not questions:
        add("What additional diligence materials can the company provide for standard verification?")

    # Keep the question list concise and user-friendly.
    questions = questions[:12]

    content = [
        "The following questions are derived from identified risks, gaps, and "
        "verification findings. They should be addressed before an investment decision."
    ]
    section = _section_base("Investor Questions", content)
    section["questions"] = questions
    section["tables"] = [
        {
            "title": "Investor questions",
            "columns": ["Question"],
            "rows": [[question] for question in questions],
        }
    ]
    section["verification_status"] = None
    return section


def _investment_considerations_section(
    overall_risk: str,
    verification_status: str,
    missing_information: List[str],
    contradictions: List[Any],
) -> Dict[str, Any]:
    considerations = [
        (
            "Investment considerations reflect the current evidence base and are not a "
            "substitute for full legal, financial, and technical diligence."
        ),
        (
            f"Overall risk is {overall_risk.lower()} and verification status is "
            f"{verification_status.lower().replace('_', ' ')}."
        ),
    ]
    if missing_information:
        considerations.append(
            "Material information is missing. Any investment decision should be "
            "conditioned on receipt and review of the missing primary documentation."
        )
    if contradictions:
        considerations.append(
            "Conflicting findings must be reconciled before relying on the analysis."
        )
    if overall_risk in {"LOW", "MEDIUM"} and not contradictions:
        considerations.append(
            "No material adverse signal was found in the available evidence, but "
            "public evidence remains unaudited and incomplete."
        )
    content = considerations
    section = _section_base("Investment Considerations", content)
    section["considerations"] = considerations
    section["verification_status"] = verification_status
    return section


def _final_assessment_section(
    overall_risk: str,
    verification_status: str,
    failed_agents: List[str],
    contradictions: List[Any],
    missing_information: List[str],
    all_findings: List[Dict[str, Any]],
) -> Dict[str, Any]:
    category = _final_category(
        overall_risk,
        verification_status,
        failed_agents,
        contradictions,
        missing_information,
        all_findings,
    )
    reasoning = [
        f"Final assessment category: {category}.",
        f"Overall risk level: {overall_risk.lower()}.",
        f"Verification status: {verification_status.lower().replace('_', ' ')}.",
    ]
    if failed_agents:
        reasoning.append(
            "Some specialist agents failed, so the report excludes their findings: "
            + ", ".join(failed_agents)
            + "."
        )
    if contradictions:
        reasoning.append(
            "Contradictions were detected between specialist findings and require "
            "reconciliation."
        )
    if missing_information:
        reasoning.append(
            f"{len(missing_information)} missing-information item(s) were recorded."
        )
    else:
        reasoning.append("No missing-information items were recorded.")
    reasoning.append(
        "The category is based on evidence-backed risk and verification status, "
        "not an arbitrary numerical score."
    )

    content = reasoning + [
        _recommendation(overall_risk, category)
    ]
    section = _section_base("Final Assessment", content)
    section["final_assessment_category"] = category
    section["final_assessment_reasoning"] = reasoning
    section["risk_indicators"] = [
        {
            "label": "Final assessment",
            "level": category,
            "reason": "Derived from risk, verification, contradictions, and missing information.",
        }
    ]
    section["verification_status"] = verification_status
    return section


def _specialist_reports(outputs: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    reports = []
    for agent_key, output in outputs.items():
        findings = [
            finding
            for finding in (output.get("findings", []) if isinstance(output, dict) else [])
            if isinstance(finding, dict)
        ]
        reports.append(
            {
                "agent_key": agent_key,
                "agent_name": output.get("agent_name", _AGENT_NAMES.get(agent_key)),
                "risk_level": output.get("risk_level", "UNKNOWN"),
                "evidence_status": output.get("evidence_status", "UNAVAILABLE"),
                "execution_status": output.get("execution_status", "UNKNOWN"),
                "investor_impact": output.get("investor_impact", ""),
                "missing_information": output.get("missing_information", []),
                "findings": findings,
            }
        )
    return reports


def _verification_summary(
    verification: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    if not verification:
        return {
            "status": "UNAVAILABLE",
            "execution_status": "FAILED",
            "issues": ["Verification output was not available."],
        }
    return {
        "status": verification.get("status", "UNAVAILABLE"),
        "verification_status": verification.get("verification_status", verification.get("status", "UNAVAILABLE")),
        "execution_status": verification.get("execution_status", "FAILED"),
        "total_findings": verification.get("total_findings", 0),
        "checked_references": verification.get("checked_references", 0),
        "valid_references": verification.get("valid_references", 0),
        "invalid_references": verification.get("invalid_references", 0),
        "unsupported_claims": verification.get("unsupported_claims", []),
        "contradictions": verification.get("contradictions", []),
        "source_reliability": verification.get("source_reliability", []),
        "missing_evidence": verification.get("missing_evidence", []),
        "detailed_reasoning": verification.get("detailed_reasoning", ""),
        "investor_impact": verification.get("investor_impact", ""),
        "issues": list(verification.get("issues", [])),
    }


def _risk_indicators(findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    indicators = []
    seen = set()
    for finding in findings:
        risk = str(finding.get("risk_level", "UNKNOWN")).upper()
        if risk not in {"MEDIUM", "HIGH", "CRITICAL"}:
            continue
        key = (finding.get("dimension"), risk)
        if key in seen:
            continue
        seen.add(key)
        indicators.append(
            {
                "label": finding.get("dimension", "Unknown dimension"),
                "level": risk,
                "reason": finding.get("summary", "Risk identified in retrieved evidence."),
            }
        )
    return indicators


def _risk_distribution_chart(findings: List[Dict[str, Any]], title: str) -> Dict[str, Any]:
    counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0, "UNKNOWN": 0}
    for finding in findings:
        risk = str(finding.get("risk_level", "UNKNOWN")).upper()
        if risk in counts:
            counts[risk] += 1
    return {
        "title": title,
        "type": "bar",
        "labels": list(counts.keys()),
        "values": list(counts.values()),
        "unit": "findings",
    }


def _verification_chart(
    verification: Optional[Dict[str, Any]],
    verification_status: str,
) -> Dict[str, Any]:
    if not verification:
        return {
            "title": "Verification status",
            "type": "status",
            "labels": [verification_status],
            "values": [1],
            "unit": "status",
        }
    return {
        "title": "Verification metrics",
        "type": "bar",
        "labels": [
            "Claims reviewed",
            "Valid references",
            "Invalid references",
            "Unsupported claims",
            "Contradictions",
        ],
        "values": [
            verification.get("total_findings", 0),
            verification.get("valid_references", 0),
            verification.get("invalid_references", 0),
            len(verification.get("unsupported_claims", []) or []),
            len(verification.get("contradictions", []) or []),
        ],
        "unit": "count",
    }


def _report_charts(
    all_findings: List[Dict[str, Any]],
    source_reliability: List[Any],
    verification: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    charts = [_risk_distribution_chart(all_findings, "Overall risk distribution")]
    if source_reliability:
        scores = [
            item.get("reliability_score", 0)
            for item in source_reliability
            if isinstance(item, dict)
        ]
        labels = [
            str(item.get("evidence_id", "source"))
            for item in source_reliability
            if isinstance(item, dict)
        ]
        charts.append(
            {
                "title": "Source reliability scores",
                "type": "bar",
                "labels": labels,
                "values": scores,
                "unit": "score",
            }
        )
    if verification:
        charts.append(_verification_chart(verification, _verification_status(verification)))
    return charts


def _truncate(value: Any, length: int) -> str:
    text = str(value or "")
    if len(text) <= length:
        return text
    return text[: length - 3].rsplit(" ", 1)[0] + "..."

def _outlook_label(overall_risk: str) -> str:
    return {
        "LOW": "Promising",
        "MEDIUM": "Promising but requires further due diligence",
        "HIGH": "High risk",
        "CRITICAL": "High risk",
        "UNKNOWN": "Insufficient information to assess",
    }.get(str(overall_risk).upper(), "Insufficient information to assess")


def _confidence_level(verification_status: str, evidence_status: str) -> str:
    status = str(verification_status or evidence_status or "").upper()
    if status == "VERIFIED":
        return "High"
    if status == "PARTIALLY_VERIFIED":
        return "Medium"
    return "Low"


def _action_section(analysis, overall_risk, missing_information, all_findings, contradictions, verification_status):
    rows = []
    for finding in all_findings:
        risk = str(finding.get("risk_level", "")).upper()
        if risk in {"HIGH", "CRITICAL"}:
            rows.append([
                "Critical" if risk == "CRITICAL" else "High",
                "Investigate " + str(finding.get("dimension", "this area")),
                "This area has a material risk signal in the retrieved evidence.",
                "Primary source documents and independent verification",
            ])
    for item in (missing_information or [])[:6]:
        rows.append([
            "High",
            "Request documentation for: " + str(item),
            "The analysis could not verify this item from public evidence.",
            "Startup-provided primary documentation",
        ])
    if contradictions:
        rows.append([
            "Critical",
            "Reconcile conflicting specialist findings",
            "Specialist agents interpreted the same evidence differently.",
            "Primary records and expert review",
        ])
    if not rows:
        rows.append([
            "Medium",
            "Complete standard document review",
            "No critical gaps were identified in the retrieved evidence.",
            "Standard diligence document package",
        ])
    rows.append([
        "Medium",
        "General due diligence suggestion: review financial statements, customer contracts, cap table, and incorporation documents",
        "These are standard investor checks and are not startup-specific findings.",
        "Startup document package",
    ])
    rows = rows[:8]
    content = [
        "Prioritized actions are based on the analysis. General suggestions are clearly labeled.",
    ]
    section = _section_base("What Should the Investor Do?", content)
    section["tables"] = [{"title": "Action plan", "columns": ["Priority", "Action Required", "Why It Matters", "Evidence Needed"], "rows": rows}]
    section["verification_status"] = verification_status
    return section


def _scorecard_section(outputs, verification, source_reliability, overall_risk):
    def status_from_risk(risk):
        risk = str(risk or "").upper()
        if risk == "LOW":
            return "Strong"
        if risk == "MEDIUM":
            return "Moderate"
        if risk in {"HIGH", "CRITICAL"}:
            return "Weak"
        return "Insufficient Data"

    financial = outputs.get("financial", {})
    marketing = outputs.get("marketing", {})
    legal = outputs.get("legal", {})
    evidence_status = str((verification or {}).get("verification_status") or (verification or {}).get("status") or "UNAVAILABLE").upper()
    evidence_status_label = "Strong" if evidence_status == "VERIFIED" else "Moderate" if evidence_status == "PARTIALLY_VERIFIED" else "Weak" if evidence_status in {"UNVERIFIED", "CONTRADICTED"} else "Insufficient Data"

    rows = [
        ["Financial Health", status_from_risk(financial.get("risk_level", "UNKNOWN")), str(financial.get("investor_impact") or "No financial assessment available."), str(financial.get("risk_level", "UNKNOWN"))],
        ["Market Opportunity", status_from_risk(marketing.get("risk_level", "UNKNOWN")), str(marketing.get("investor_impact") or "No market assessment available."), str(marketing.get("risk_level", "UNKNOWN"))],
        ["Marketing and Customer Traction", status_from_risk(marketing.get("risk_level", "UNKNOWN")), "Derived from retrieved market evidence.", str(marketing.get("evidence_status", "UNAVAILABLE"))],
        ["Legal and Compliance", status_from_risk(legal.get("risk_level", "UNKNOWN")), str(legal.get("investor_impact") or "No legal assessment available."), str(legal.get("risk_level", "UNKNOWN"))],
        ["Evidence Reliability", evidence_status_label, "Based on verification of specialist claims against stored evidence.", evidence_status],
    ]
    content = [
        "Scores are qualitative assessments, not fabricated numerical scores.",
    ]
    section = _section_base("Investment Scorecard", content)
    section["tables"] = [{"title": "Scorecard", "columns": ["Category", "Status", "Explanation", "Supporting Signal"], "rows": rows}]
    section["verification_status"] = evidence_status
    return section


def _positives_section(all_findings, outputs):
    positives = [f for f in all_findings if str(f.get("risk_level", "")).upper() == "LOW"]
    content = [
        "These are the strongest positive signals found in the retrieved evidence. They are not proof of investment quality."
    ] if positives else [
        "No strong positive signals were identified in the retrieved evidence."
    ]
    section = _section_base("Reasons to Consider Investing", content)
    section["findings"] = [
        {
            "dimension": f.get("dimension"),
            "summary": f.get("summary"),
            "risk_level": f.get("risk_level"),
            "evidence_status": f.get("evidence_status"),
            "investor_impact": f.get("investor_impact"),
            "evidence_references": f.get("evidence_references", []),
        }
        for f in positives
    ]
    return section


def _risks_section(all_findings, outputs):
    risks = [f for f in all_findings if str(f.get("risk_level", "")).upper() in {"MEDIUM", "HIGH", "CRITICAL"}]
    content = [
        "Risks are grouped by severity. Each risk is only as strong as its underlying evidence."
    ]
    section = _section_base("Major Risks and Red Flags", content)
    section["findings"] = [
        {
            "dimension": f.get("dimension"),
            "summary": f.get("summary"),
            "risk_level": f.get("risk_level"),
            "evidence_status": f.get("evidence_status"),
            "investor_impact": f.get("investor_impact"),
            "evidence_references": f.get("evidence_references", []),
        }
        for f in risks
    ]
    section["risk_indicators"] = _risk_indicators(risks)
    return section


def _agent_analysis_section(analysis, outputs, verification, all_findings):
    content = []
    for key in ["financial", "marketing", "legal"]:
        output = outputs.get(key, {})
        name = {"financial": "Financial Agent", "marketing": "Marketing Agent", "legal": "Legal Agent"}[key]
        content.append(
            name + ": Overall risk " + str(output.get("risk_level", "UNKNOWN")) + "; evidence status " + str(output.get("evidence_status", "UNAVAILABLE")) + ". " +
            str(output.get("investor_impact") or "No investor impact summary available.")
        )
        missing = output.get("missing_information") or []
        if missing:
            content.append(name + " missing information: " + "; ".join(str(x) for x in missing[:5]) + ".")
    if verification:
        content.append(
            "Verification Agent: " + str(verification.get("verification_status") or verification.get("status") or "UNAVAILABLE") + ". " +
            str(verification.get("detailed_reasoning") or "")
        )
    content.append("Controller Agent: Synthesis is based on specialist findings and verification results. No unsupported conclusions are added.")
    section = _section_base("Agent-by-Agent Analysis", content)
    section["findings"] = [
        {
            "dimension": f.get("dimension"),
            "summary": f.get("summary"),
            "risk_level": f.get("risk_level"),
            "evidence_status": f.get("evidence_status"),
            "agent": f.get("agent_name"),
        }
        for f in all_findings
    ]
    return section


def _missing_section(missing_information, all_findings, failed_agents):
    content = [
        "The following items were not available in the retrieved evidence. They are reported, not estimated."
    ]
    if not missing_information and not failed_agents:
        content.append("No information gaps were identified in the retrieved evidence set.")
    section = _section_base("Missing Information and Due Diligence Checklist", content)
    section["tables"] = [{"title": "Missing information", "columns": ["Gap"], "rows": [[item] for item in (missing_information or [])]}]
    if failed_agents:
        section["tables"].append({"title": "Failed specialist agents", "columns": ["Agent"], "rows": [[agent] for agent in failed_agents]})
    checklist = [
        "Financial statements",
        "Revenue breakdown",
        "Customer contracts",
        "Customer retention data",
        "Cap table",
        "Incorporation documents",
        "Intellectual property ownership documents",
    ]
    section["tables"].append({"title": "Due diligence checklist", "columns": ["Item"], "rows": [[item] for item in checklist]})
    return section


def _evidence_section(evidence_references, verification):
    content = [
        "Sources are listed with their verification status. Links are provided when available."
    ]
    section = _section_base("Evidence and Sources", content)
    section["evidence_references"] = [r for r in (evidence_references or []) if isinstance(r, dict)]
    if verification:
        for ref in (verification.get("supporting_evidence") or []):
            if isinstance(ref, dict) and ref not in section["evidence_references"]:
                section["evidence_references"].append(ref)
    return section


def _final_guidance_section(analysis, overall_risk, verification_status, final_category, missing_information, all_findings):
    most_important_risk = "None identified"
    risks = [f for f in all_findings if str(f.get("risk_level", "")).upper() in {"HIGH", "CRITICAL"}]
    if risks:
        most_important_risk = str(risks[0].get("dimension") or risks[0].get("summary") or "High risk finding")
    what_must_verify = [str(x) for x in (missing_information or ["No additional verification items identified."])[:3]]
    content = [
        "Investment Outlook: " + _outlook_label(overall_risk),
        "Main Reason: " + str(analysis.startup_name) + " was assessed using retrieved public evidence and specialist analysis.",
        "Most Important Risk: " + most_important_risk,
        "Next Step: " + _recommendation(overall_risk, final_category),
        "What Must Be Verified Before Proceeding: " + "; ".join(what_must_verify),
    ]
    section = _section_base("Final Investor Decision Guidance", content)
    section["final_assessment_category"] = final_category
    return section
