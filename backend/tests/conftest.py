"""
Shared test setup.

The environment variables are set BEFORE the app is imported, so the tests use
a temporary database and never touch backend/rxresolve.db. Ollama is disabled
so results are the same on every machine.
"""
import os
import tempfile

TEST_DIR = tempfile.mkdtemp(prefix="rxresolve_test_")
os.environ["RXR_DATABASE_PATH"] = os.path.join(TEST_DIR, "test.db")
os.environ["RXR_USE_OLLAMA"] = "0"
os.environ["RXR_SEED_DEMO_DATA"] = "1"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:  # "with" runs the startup code (tables + demo data)
        yield test_client


@pytest.fixture(scope="session")
def auth_headers(client):
    response = client.post("/api/login", json={"username": "admin", "password": "admin123"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['token']}"}


@pytest.fixture
def new_case_payload():
    return {
        "patient_id": "PT-TEST-1",
        "claim_id": "RX-TEST-1",
        "medication": "ExampleMed",
        "insurance": "DemoHealth",
        "rejection_code": "PA001",
        "rejection_message": "Prior authorization required",
        "quantity": "30",
        "date_of_service": "2026-09-01",
    }
