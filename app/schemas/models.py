from pydantic import BaseModel
from pydantic import Field


class IntakeRequest(BaseModel):
    title: str = Field(min_length=6)
    details: str = Field(min_length=12)
    source: str = Field(default="form")
    requester_team: str | None = None
    affected_system: str | None = None


class IntakeAssessment(BaseModel):
    triage_category: str
    priority: str
    queue: str
    recommended_owner: str
    due_window: str
    summary: str
    next_actions: list[str]
    missing_fields: list[str]
    risk_flags: list[str]

