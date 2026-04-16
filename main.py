from app.api.routes import router
from fastapi import FastAPI


app = FastAPI(
    title="ops-intake-hub",
    description="Deterministic intake triage API for operational work.",
    version="0.1.0",
)
app.include_router(router)

