from datetime import datetime
from typing import Any, Dict, List, Optional

from app.db.models import Analysis, Startup

_RISK_ORDER = {
    "UNKNOWN": 0,
    "LOW": 1,
    "MEDIUM": 2,
    "HIGH": 3,
    "CRITICAL": 4,
}


def generate_final_report(
    analysis: Analysis,
    startup: Startup,
    specialist_outputs: Dict[str, Any],
    specialist_errors: Dict[str, Any],
    verification: Optional[Dict[str, Any]],
    aggregation: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    outputs = _outputs(specialist_outputs)
    overall_risk = _overall_risk(outputs, aggregation)
    missing_information = _missing_information(outputs)
    failed_agents = sorted(specialist_errors)
    assessment = _assessment(overall_risk)

    specialist_sections = []
    for agent_key, output in outputs.items():
        findings = []
        for finding in output.get("findings", []):
            if isinstance(finding, dict):
                findings.append(
                    {
                        "dimension": finding.get("dimension"),
                        "summary": finding.get("summary"),
                        "risk_level": finding.get("risk_level"),
                        "evidence_status": finding.get("evidence_status"),
                        "investor_impact": finding.get("investor_impact"),
                    }
                )
        specialist_sections.append(
            {
                "agent_key": agent_key,
                "agent_name": output.get("agent_name"),
                "risk_level": output.get("risk_level"),
                "evidence_status": output.get("evidence_status"),
                "execution_status": output.get("execution_status"),
                "investor_impact": output.get("investor_impact"),
                "findings": findings,
            }
        )

    verification_summary = _verification_summary(verification)
    generated_at = datetime.utcnow().isoformat() + "Z"

    return {
        "title": f"{analysis.startup_name} Due Diligence Report",
        "generated_at": generated_at,
        "company": {
            "analysis_id": analysis.id,
            "startup_id": startup.id,
            "name": analysis.startup_name,
            "website": analysis.website,
            "industry": analysis.industry,
            "country": analysis.country,
        },
        "overall_risk": overall_risk,
        "overall_assessment": assessment,
        "evidence_status": (
            aggregation.get("evidence_status")
            if aggregation
            else _overall_evidence_status(outputs)
        ),
        "recommendation": _recommendation(overall_risk),
        "executive_summary": _executive_summary(
            analysis.startup_name,
            overall_risk,
            len(outputs),
            failed_agents,
        ),
        "specialist_reports": specialist_sections,
        "verification": verification_summary,
        "failed_agents": failed_agents,
        "missing_information": missing_information,
        "disclaimer": (
            "This report is limited to the retrieved public evidence and does "
            "not constitute independent verification, legal advice, an audit, "
            "or a recommendation to invest."
        ),
    }


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
    statuses = [str(output.get("evidence_status", "UNAVAILABLE")) for output in outputs.values()]
    if not statuses:
        return "UNAVAILABLE"
    if all(status == "VERIFIED" for status in statuses):
        return "VERIFIED"
    if any(status in {"VERIFIED", "PARTIALLY_VERIFIED"} for status in statuses):
        return "PARTIALLY_VERIFIED"
    if any(status == "UNVERIFIED" for status in statuses):
        return "UNVERIFIED"
    return "UNAVAILABLE"


def _missing_information(outputs: Dict[str, Dict[str, Any]]) -> List[str]:
    missing = []
    seen = set()
    for output in outputs.values():
        for item in output.get("missing_information", []):
            if item in seen:
                continue
            seen.add(item)
            missing.append(item)
    return missing


def _assessment(overall_risk: str) -> str:
    return {
        "CRITICAL": "Critical risk",
        "HIGH": "High risk",
        "MEDIUM": "Moderate risk",
        "LOW": "Low risk",
        "UNKNOWN": "Insufficient evidence",
    }.get(overall_risk, "Insufficient evidence")


def _recommendation(overall_risk: str) -> str:
    return {
        "CRITICAL": (
            "Do not proceed until the critical diligence issues are resolved "
            "and independently verified."
        ),
        "HIGH": (
            "Resolve the high-risk findings and obtain primary documentation "
            "before relying on this analysis."
        ),
        "MEDIUM": (
            "Complete further diligence and corroborate the open findings "
            "before making an investment decision."
        ),
        "LOW": (
            "No material adverse signal was found in the available evidence, "
            "but full diligence and primary-source verification are still "
            "required."
        ),
        "UNKNOWN": (
            "Insufficient evidence is available to support an investment "
            "decision. Obtain primary documentation before proceeding."
        ),
    }.get(overall_risk, "Further diligence is required.")


def _executive_summary(
    name: str,
    overall_risk: str,
    output_count: int,
    failed_agents: List[str],
) -> str:
    summary = (
        f"{name} was assessed using {output_count} specialist agent "
        f"report(s). The aggregate evidence-backed risk level is "
        f"{overall_risk.lower()}."
    )
    if failed_agents:
        summary += (
            " The following specialist agents failed and are excluded from "
            "the completed findings: " + ", ".join(failed_agents) + "."
        )
    return summary


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
        "execution_status": verification.get("execution_status", "FAILED"),
        "total_findings": verification.get("total_findings", 0),
        "checked_references": verification.get("checked_references", 0),
        "valid_references": verification.get("valid_references", 0),
        "invalid_references": verification.get("invalid_references", 0),
        "issues": list(verification.get("issues", [])),
    }
