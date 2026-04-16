from app.schemas.models import IntakeRequest
from app.services.triage import IntakeTriageService


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
    assert any("security review" in action.lower() for action in assessment.next_actions)

