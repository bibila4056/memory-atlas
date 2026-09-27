"""FastAPI entry point for the Memory Atlas MVP."""

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .models import ResolvedVisualPlan
from .capture_routes import router as capture_router
from .transcription_routes import router as transcription_router
from .weave_routes import router as weave_router
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[3] / ".env")


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "resolved_visual_plan.json"

app = FastAPI(title="Memory Atlas API", version="0.1.0")
app.include_router(capture_router)
app.include_router(transcription_router)
app.include_router(weave_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


def load_demo_plan() -> ResolvedVisualPlan:
    """Load and validate the deterministic demo plan before it leaves the API."""

    return ResolvedVisualPlan.model_validate_json(FIXTURE_PATH.read_text())


@app.get("/health" if os.getenv("VERCEL") else "/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/plans/demo" if os.getenv("VERCEL") else "/api/plans/demo", response_model=ResolvedVisualPlan)
def get_demo_plan() -> ResolvedVisualPlan:
    return load_demo_plan()
