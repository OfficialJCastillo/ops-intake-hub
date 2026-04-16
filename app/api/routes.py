from app.api.demo_ui import render_demo_ui
from app.schemas.models import IntakeAssessment
from app.schemas.models import IntakeRequest
from app.services.triage import IntakeTriageService
from fastapi import APIRouter


router = APIRouter()
triage_service = IntakeTriageService()


@router.get("/", include_in_schema=False)
def demo_ui():
    return render_demo_ui()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/triage/assess", response_model=IntakeAssessment)
def assess_intake(request: IntakeRequest) -> IntakeAssessment:
    return triage_service.assess(request)

