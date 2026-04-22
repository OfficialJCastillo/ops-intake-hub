from app.schemas.models import IntakeAssessment
from app.schemas.models import IntakeRequest
from app.schemas.models import TriageCategoryRule
from app.schemas.models import TriageRulesResponse


PRIORITY_DUE_WINDOWS = {
    "critical": "within 30 minutes",
    "high": "same business day",
    "medium": "within 2 business days",
    "normal": "within 5 business days",
}

PRIORITY_SIGNALS = {
    "critical": ["incident category", "outage", "downtime", "rollback", "sev"],
    "high": ["asap", "urgent", "today", "immediately", "customer escalation", "bug report"],
    "medium": ["this week", "next week", "soon", "weekday deadline"],
    "normal": ["no urgent timing or impact signal"],
}

CATEGORY_RULES = {
    "incident": {
        "queue": "incident-command",
        "owner": "incident lead",
        "default_priority": "critical",
        "required_fields": ["requester_team", "affected_system", "customer impact", "response window"],
        "routing_signals": ["outage", "incident", "rollback", "sev", "downtime"],
        "risk_signals": ["customer downtime", "executive updates", "mitigation ambiguity"],
    },
    "access_request": {
        "queue": "it-operations",
        "owner": "it operations",
        "default_priority": "normal",
        "required_fields": ["requester_team", "affected_system", "role or permission scope", "approval owner"],
        "routing_signals": ["access", "permission", "role", "provision"],
        "risk_signals": ["over-provisioning", "missing approval"],
    },
    "vendor_request": {
        "queue": "business-operations",
        "owner": "business operations",
        "default_priority": "normal",
        "required_fields": ["requester_team", "spend range", "data handling scope", "target decision date"],
        "routing_signals": ["vendor", "procurement", "purchase", "contract"],
        "risk_signals": ["security review", "budget ambiguity", "contract timing"],
    },
    "customer_escalation": {
        "queue": "customer-ops",
        "owner": "support lead",
        "default_priority": "high",
        "required_fields": ["requester_team", "customer or account identifier", "impact summary", "next update time"],
        "routing_signals": ["customer", "escalation", "blocked account", "vip"],
        "risk_signals": ["communication drift", "missed promised update"],
    },
    "bug_report": {
        "queue": "engineering-triage",
        "owner": "engineering manager",
        "default_priority": "high",
        "required_fields": ["requester_team", "affected_system", "reproduction details", "severity expectation"],
        "routing_signals": ["bug", "failure", "defect", "broken"],
        "risk_signals": ["weak reproduction steps", "unclear severity"],
    },
    "general_operations": {
        "queue": "operations-inbox",
        "owner": "operations manager",
        "default_priority": "normal",
        "required_fields": ["requester_team", "desired outcome", "deadline or checkpoint"],
        "routing_signals": ["fallback for uncategorized operations work"],
        "risk_signals": ["ambiguous owner", "hidden dependencies"],
    },
}


class IntakeTriageService:
    def rules(self) -> TriageRulesResponse:
        return TriageRulesResponse(
            priority_due_windows=PRIORITY_DUE_WINDOWS,
            priority_signals=PRIORITY_SIGNALS,
            category_rules=[
                TriageCategoryRule(
                    triage_category=category,
                    queue=rule["queue"],
                    recommended_owner=rule["owner"],
                    default_priority=rule["default_priority"],
                    required_fields=rule["required_fields"],
                    routing_signals=rule["routing_signals"],
                    risk_signals=rule["risk_signals"],
                )
                for category, rule in CATEGORY_RULES.items()
            ],
        )

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
            sla_policy=f"{priority} priority routes {category.replace('_', ' ')} intake {due_window}.",
            summary=summary,
            routing_rationale=self._routing_rationale(request, category, priority, queue, owner, due_window),
            next_actions=self._next_actions(request, category, priority),
            missing_fields=self._missing_fields(request, category),
            risk_flags=self._risk_flags(request, category, priority),
        )

    def _detect_category(self, request: IntakeRequest) -> str:
        text = self._text(request)
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
        text = self._text(request)
        if category == "incident":
            return "critical"
        if any(token in text for token in ["asap", "urgent", "today", "tomorrow", "immediately", "blocked"]):
            return "high"
        if category in {"customer_escalation", "bug_report"}:
            return "high"
        if any(
            token in text
            for token in [
                "this week",
                "next week",
                "soon",
                "monday",
                "tuesday",
                "wednesday",
                "thursday",
                "friday",
                "end of week",
            ]
        ):
            return "medium"
        return "normal"

    def _queue_for(self, category: str, priority: str) -> str:
        if category == "incident":
            return CATEGORY_RULES[category]["queue"]
        if category == "bug_report" and priority in {"critical", "high"}:
            return "engineering-triage"
        return CATEGORY_RULES[category]["queue"]

    def _owner_for(self, category: str) -> str:
        return CATEGORY_RULES[category]["owner"]

    def _due_window_for(self, priority: str) -> str:
        return PRIORITY_DUE_WINDOWS[priority]

    def _build_summary(self, request: IntakeRequest, category: str, priority: str, queue: str) -> str:
        source = request.source.replace("_", " ")
        return (
            f"Triage this {category.replace('_', ' ')} from {source} as {priority} priority "
            f"and route it to {queue}."
        )

    def _next_actions(self, request: IntakeRequest, category: str, priority: str) -> list[str]:
        text = self._text(request)
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
        text = self._text(request)
        if self._blank(request.requester_team):
            missing.append("Requester team")
        if category in {"incident", "access_request", "bug_report"} and self._blank(request.affected_system):
            missing.append("Affected system")
        if category == "incident" and not any(token in text for token in ["customer", "blocked", "down", "impact", "affected"]):
            missing.append("Customer impact summary")
        if category == "access_request" and not any(
            token in text for token in ["admin", "read", "write", "viewer", "editor", "role", "permission"]
        ):
            missing.append("Role or permission scope")
        if category == "access_request" and not any(token in text for token in ["approve", "approval", "manager", "owner"]):
            missing.append("Approval owner")
        if category == "vendor_request" and not any(token in text for token in ["budget", "spend", "cost", "$"]):
            missing.append("Estimated spend or budget owner")
        if category == "vendor_request" and not any(token in text for token in ["data", "security", "privacy", "regulated"]):
            missing.append("Data handling scope")
        if category == "customer_escalation" and not any(token in text for token in ["account", "customer", "vip"]):
            missing.append("Customer or account identifier")
        if category == "bug_report" and not any(token in text for token in ["repro", "reproduce", "steps", "when", "after"]):
            missing.append("Reproduction details")
        if category == "bug_report" and not any(token in text for token in ["severity", "sev", "p0", "p1", "p2"]):
            missing.append("Severity expectation")
        if category == "general_operations" and self._is_vague(text):
            missing.append("Desired outcome")
        if not any(
            token in text
            for token in [
                "asap",
                "urgent",
                "immediately",
                "today",
                "tomorrow",
                "monday",
                "tuesday",
                "wednesday",
                "thursday",
                "friday",
                "week",
                "date",
                "by ",
            ]
        ):
            missing.append("Requested deadline or response window")
        return self._dedupe(missing)

    def _risk_flags(self, request: IntakeRequest, category: str, priority: str) -> list[str]:
        flags = []
        text = self._text(request)
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
        if category == "bug_report" and "repro" not in text and "steps" not in text:
            flags.append("Weak reproduction detail can slow engineering triage.")
        if category == "vendor_request" and not any(token in text for token in ["budget", "spend", "cost", "$"]):
            flags.append("Budget ambiguity can stall procurement routing.")
        return self._dedupe(flags)

    def _routing_rationale(
        self,
        request: IntakeRequest,
        category: str,
        priority: str,
        queue: str,
        owner: str,
        due_window: str,
    ) -> list[str]:
        source = request.source.replace("_", " ")
        return [
            f"Matched {category.replace('_', ' ')} routing signals from the intake text.",
            f"Applied {priority} SLA policy: {due_window}.",
            f"Routed from {source} to {queue} with {owner} as the first owner.",
        ]

    def _text(self, request: IntakeRequest) -> str:
        return f"{request.title} {request.details}".lower()

    def _blank(self, value: str | None) -> bool:
        return value is None or not value.strip()

    def _is_vague(self, text: str) -> bool:
        words = [word.strip(".,!?") for word in text.split() if word.strip(".,!?")]
        return len(words) < 8 or "need help" in text

    def _dedupe(self, items: list[str]) -> list[str]:
        seen = set()
        ordered = []
        for item in items:
            if item not in seen:
                seen.add(item)
                ordered.append(item)
        return ordered
