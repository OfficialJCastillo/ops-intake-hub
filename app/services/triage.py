from app.schemas.models import IntakeAssessment
from app.schemas.models import IntakeRequest


class IntakeTriageService:
    def assess(self, request: IntakeRequest) -> IntakeAssessment:
        category = self._detect_category(request)
        priority = self._detect_priority(request, category)
        queue = self._queue_for(category, priority)
        owner = self._owner_for(category)
        due_window = self._due_window_for(priority)
        summary = self._build_summary(request, category, priority, queue)

        return IntakeAssessment(
            triage_category=category,
            priority=priority,
            queue=queue,
            recommended_owner=owner,
            due_window=due_window,
            summary=summary,
            next_actions=self._next_actions(request, category, priority),
            missing_fields=self._missing_fields(request, category),
            risk_flags=self._risk_flags(request, category, priority),
        )

    def _detect_category(self, request: IntakeRequest) -> str:
        text = f"{request.title} {request.details}".lower()
        if any(token in text for token in ["outage", "incident", "rollback", "sev", "downtime"]):
            return "incident"
        if any(token in text for token in ["access", "permission", "role", "provision"]):
            return "access_request"
        if any(token in text for token in ["vendor", "procurement", "purchase", "contract"]):
            return "vendor_request"
        if any(token in text for token in ["customer", "escalation", "blocked account", "vip"]):
            return "customer_escalation"
        if any(token in text for token in ["bug", "failure", "defect", "broken"]):
            return "bug_report"
        return "general_operations"

    def _detect_priority(self, request: IntakeRequest, category: str) -> str:
        text = f"{request.title} {request.details}".lower()
        if category == "incident":
            return "critical"
        if any(token in text for token in ["asap", "urgent", "today", "immediately"]):
            return "high"
        if category in {"customer_escalation", "bug_report"}:
            return "high"
        if any(token in text for token in ["this week", "soon", "thursday", "friday"]):
            return "medium"
        return "normal"

    def _queue_for(self, category: str, priority: str) -> str:
        if category == "incident":
            return "incident-command"
        if category == "access_request":
            return "it-operations"
        if category == "vendor_request":
            return "business-operations"
        if category == "customer_escalation":
            return "customer-ops"
        if category == "bug_report" and priority in {"critical", "high"}:
            return "engineering-triage"
        return "operations-inbox"

    def _owner_for(self, category: str) -> str:
        owners = {
            "incident": "incident lead",
            "access_request": "it operations",
            "vendor_request": "business operations",
            "customer_escalation": "support lead",
            "bug_report": "engineering manager",
            "general_operations": "operations manager",
        }
        return owners[category]

    def _due_window_for(self, priority: str) -> str:
        windows = {
            "critical": "within 30 minutes",
            "high": "same business day",
            "medium": "within 2 business days",
            "normal": "within 5 business days",
        }
        return windows[priority]

    def _build_summary(self, request: IntakeRequest, category: str, priority: str, queue: str) -> str:
        source = request.source.replace("_", " ")
        return (
            f"Triage this {category.replace('_', ' ')} from {source} as {priority} priority "
            f"and route it to {queue}."
        )

    def _next_actions(self, request: IntakeRequest, category: str, priority: str) -> list[str]:
        text = f"{request.title} {request.details}".lower()
        actions = {
            "incident": [
                "Assign an incident lead and confirm current impact.",
                "Open a communication thread for responders and stakeholders.",
                "Define the immediate mitigation or rollback path.",
            ],
            "access_request": [
                "Verify requester identity and access scope.",
                "Confirm the target system and required role level.",
                "Record approval requirements before provisioning.",
            ],
            "vendor_request": [
                "Capture business need, spend range, and approval owner.",
                "Route for security or data review if external tooling is involved.",
                "Confirm contract and procurement path before commitment.",
            ],
            "customer_escalation": [
                "Confirm customer impact and response owner.",
                "Summarize current issue state and promised next update.",
                "Escalate to the correct functional team with urgency context.",
            ],
            "bug_report": [
                "Confirm reproduction details and affected system.",
                "Set severity and assign the owning engineering queue.",
                "Document the validation or rollback expectation.",
            ],
            "general_operations": [
                "Clarify the requested outcome and operating deadline.",
                "Identify dependencies and approval points.",
                "Assign an owner and next checkpoint.",
            ],
        }
        result = list(actions[category])
        if priority == "critical":
            result.insert(0, "Acknowledge receipt immediately and start incident coordination.")
        if category == "vendor_request" and "data" in text:
            result.insert(1, "Confirm whether a security review is required for external data handling.")
        return result

    def _missing_fields(self, request: IntakeRequest, category: str) -> list[str]:
        missing = []
        if request.requester_team is None:
            missing.append("Requester team")
        if category in {"incident", "access_request", "bug_report"} and request.affected_system is None:
            missing.append("Affected system")
        text = f"{request.title} {request.details}".lower()
        if not any(token in text for token in ["today", "tomorrow", "thursday", "friday", "week", "date"]):
            missing.append("Requested deadline or response window")
        return missing

    def _risk_flags(self, request: IntakeRequest, category: str, priority: str) -> list[str]:
        flags = []
        text = f"{request.title} {request.details}".lower()
        if priority in {"critical", "high"}:
            flags.append("Delayed routing will increase operational churn.")
        if category == "incident":
            flags.append("Customer-facing downtime may require executive updates.")
        if category == "access_request":
            flags.append("Provisioning mistakes can create security exposure.")
        if category == "vendor_request" and "data" in text:
            flags.append("External data handling may trigger security review.")
        if "customer" in text:
            flags.append("Customer impact increases communication risk.")
        return flags
