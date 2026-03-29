import asyncio
from importlib import import_module
from fastapi.testclient import TestClient
import pytest

from app.db.base import Base
from app.db.session import engine
import app.models.db_models  # ensure models are registered
from app.services import ai
from app.models.schemas import AnalysisResult as AnalysisResultSchema

# Avoid name shadowing with the package by importing dynamically
fastapi_app = import_module("app.main").app


@pytest.fixture(autouse=True)
def reset_db():
    async def _reset():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_reset())


@pytest.fixture(autouse=True)
def stub_ai(monkeypatch):
    async def fake_analyze(logs, correlation_id=None):
        return AnalysisResultSchema(
            root_cause="stub root cause",
            impact="stub impact",
            fix="stub fix",
            correlation_id=correlation_id,
        )

    monkeypatch.setattr(ai.airca, "analyze", fake_analyze)


@pytest.fixture
def client():
    import fastapi
    c = TestClient(fastapi_app)
    # When wrapped, TestClient may wrap FastAPI or _WrapASGI2 depending on version
    underlying = getattr(c.app, "app", c.app)
    assert isinstance(underlying, fastapi.FastAPI)
    return c


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json().get("status") == "ok"


def test_logs_analyze_flow(client):
    payload = [
        {
            "source": "jenkins",
            "service": "deploy-pipeline",
            "message": "Terraform apply failed: Error acquiring the state lock",
        },
        {
            "source": "terraform",
            "service": "networking",
            "message": "Error acquiring the state lock",
        },
        {
            "source": "kubernetes",
            "service": "payments-api",
            "message": "Back-off restarting failed container",
        },
    ]

    r = client.post("/logs", json=payload)
    assert r.status_code == 200, r.text
    assert r.json().get("stored") == 3

    analyze_resp = client.post("/analyze", json={"use_ai": True})
    assert analyze_resp.status_code == 200, analyze_resp.text
    data = analyze_resp.json()
    assert data["correlation_id"]
    assert data["findings"]
    assert data["analysis"]["root_cause"]
    assert data["analysis"]["fix"]

    findings_resp = client.get("/findings")
    assert findings_resp.status_code == 200
    findings = findings_resp.json()
    assert len(findings) >= 1
