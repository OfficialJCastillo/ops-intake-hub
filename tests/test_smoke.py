from app.schemas.models import IntakeRequest
from app.services.triage import IntakeTriageService


def test_rules_expose_priority_and_category_policy() -> None:
    rules = IntakeTriageService().rules()

    assert rules.priority_due_windows["critical"] == "within 30 minutes"
    assert rules.priority_due_windows["high"] == "same business day"
    assert any(rule.triage_category == "vendor_request" for rule in rules.category_rules)
    assert any("budget ambiguity" in rule.risk_signals for rule in rules.category_rules if rule.triage_category == "vendor_request")


def test_incident_intake_gets_critical_priority() -> None:
    assessment = IntakeTriageService().assess(
        IntakeRequest(
            title="Customer outage on billing portal",
            details="Multiple customers are blocked today and a rollback may be needed immediately.",
            source="slack",
            requester_team="Finance Operations",
            affected_system="billing-portal",
        )
    )

    assert assessment.triage_category == "incident"
    assert assessment.priority == "critical"
    assert assessment.queue == "incident-command"
    assert "within 30 minutes" == assessment.due_window
    assert "critical priority" in assessment.sla_policy
    assert any("incident routing signals" in rationale for rationale in assessment.routing_rationale)
    assert assessment.risk_flags


def test_access_request_highlights_missing_fields() -> None:
    assessment = IntakeTriageService().assess(
        IntakeRequest(
            title="Provision finance role access",
            details="Need permission updates for the new analyst this week.",
            source="form",
        )
    )

    assert assessment.triage_category == "access_request"
    assert "Requester team" in assessment.missing_fields
    assert "Affected system" in assessment.missing_fields
    assert "Approval owner" in assessment.missing_fields
    assert assessment.recommended_owner == "it operations"


def test_vendor_request_routes_to_business_operations() -> None:
    assessment = IntakeTriageService().assess(
        IntakeRequest(
            title="New analytics vendor review",
            details="Need procurement help for a data vendor contract next week.",
            source="email",
            requester_team="Data",
        )
    )

    assert assessment.triage_category == "vendor_request"
    assert assessment.queue == "business-operations"
    assert "Estimated spend or budget owner" in assessment.missing_fields
    assert any("security review" in action.lower() for action in assessment.next_actions)


def test_bug_report_requests_reproduction_and_severity_context() -> None:
    assessment = IntakeTriageService().assess(
        IntakeRequest(
            title="Broken export button",
            details="The CSV export fails for finance users this week.",
            source="form",
            requester_team="Finance Operations",
            affected_system="reporting",
        )
    )

    assert assessment.triage_category == "bug_report"
    assert assessment.priority == "high"
    assert "Reproduction details" in assessment.missing_fields
    assert "Severity expectation" in assessment.missing_fields
    assert any("reproduction detail" in flag.lower() for flag in assessment.risk_flags)
