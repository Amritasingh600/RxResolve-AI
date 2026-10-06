def test_login_success_and_failure(client):
    assert client.post("/api/login", json={"username": "staff", "password": "staff123"}).status_code == 200
    bad = client.post("/api/login", json={"username": "admin", "password": "wrong"})
    assert bad.status_code == 401
    assert "Invalid" in bad.json()["detail"]


def test_endpoints_require_login(client):
    assert client.get("/api/cases").status_code == 401
    assert client.get("/api/cases", headers={"Authorization": "Bearer not-a-real-token"}).status_code == 401


def test_sample_cases_are_seeded(client, auth_headers):
    cases = client.get("/api/cases", headers=auth_headers).json()
    assert len(cases) >= 10


def test_create_and_get_case(client, auth_headers, new_case_payload):
    created = client.post("/api/cases", json=new_case_payload, headers=auth_headers)
    assert created.status_code == 201
    case = created.json()
    assert case["status"] == "New"
    assert case["category"] is None

    fetched = client.get(f"/api/cases/{case['id']}", headers=auth_headers)
    assert fetched.status_code == 200
    assert fetched.json()["medication"] == "ExampleMed"
    assert fetched.json()["history"][0]["new_status"] == "New"


def test_full_demo_workflow(client, auth_headers, new_case_payload):
    case_id = client.post("/api/cases", json=new_case_payload, headers=auth_headers).json()["id"]

    # Analyze
    analyzed = client.post(f"/api/cases/{case_id}/analyze", headers=auth_headers).json()
    assert analyzed["category"] == "Prior Authorization Required"
    assert analyzed["confidence"] >= 0.8
    assert analyzed["status"] == "PA Required"
    assert analyzed["policy_matches"][0]["source"] == "prior_authorization.txt"
    assert analyzed["analysis_source"] == "rule-based"
    assert len(analyzed["pa_checklist"]) > 0

    # PA draft
    drafted = client.post(f"/api/cases/{case_id}/pa-draft", headers=auth_headers).json()
    assert "AI-GENERATED DRAFT — REQUIRES HUMAN REVIEW" in drafted["pa_draft"]
    assert "has NOT been submitted" in drafted["pa_draft"]

    # Tick a manual checklist item; automatic items cannot be forced
    items = [dict(item) for item in drafted["pa_checklist"]]
    for item in items:
        if item["key"] in ("policy_reviewed", "prescriber_info"):
            item["done"] = True
    updated = client.put(f"/api/cases/{case_id}/pa-checklist", json={"items": items}, headers=auth_headers).json()
    by_key = {item["key"]: item["done"] for item in updated["pa_checklist"]}
    assert by_key["policy_reviewed"] is True
    assert by_key["prescriber_info"] is False  # no prescriber on the case

    # Status change is recorded in the history
    changed = client.put(f"/api/cases/{case_id}/status", json={"status": "Submitted", "note": "Sent by staff"}, headers=auth_headers).json()
    assert changed["status"] == "Submitted"
    assert changed["history"][-1]["old_status"] == "PA Required"
    assert changed["history"][-1]["new_status"] == "Submitted"


def test_search_and_filter(client, auth_headers):
    by_medication = client.get("/api/cases", params={"q": "Cardiozen"}, headers=auth_headers).json()
    assert by_medication and all("Cardiozen" in c["medication"] for c in by_medication)

    resolved = client.get("/api/cases", params={"status": "Resolved"}, headers=auth_headers).json()
    assert resolved and all(c["status"] == "Resolved" for c in resolved)

    step = client.get("/api/cases", params={"category": "Step Therapy"}, headers=auth_headers).json()
    assert step and all(c["category"] == "Step Therapy" for c in step)

    by_id = client.get("/api/cases", params={"q": "#1"}, headers=auth_headers).json()
    assert any(c["id"] == 1 for c in by_id)


def test_update_and_delete_case(client, auth_headers, new_case_payload):
    case_id = client.post("/api/cases", json=new_case_payload, headers=auth_headers).json()["id"]
    updated = client.put(f"/api/cases/{case_id}", json={"prescriber": "Dr. Test"}, headers=auth_headers)
    assert updated.json()["prescriber"] == "Dr. Test"

    assert client.delete(f"/api/cases/{case_id}", headers=auth_headers).status_code == 204
    assert client.get(f"/api/cases/{case_id}", headers=auth_headers).status_code == 404


def test_dashboard(client, auth_headers):
    data = client.get("/api/dashboard", headers=auth_headers).json()
    assert data["total_cases"] == data["pending_cases"] + data["resolved_cases"]
    assert data["pa_cases"] >= 1
    assert len(data["recent_cases"]) > 0


# ------------------------------------------------------ invalid input -----
def test_create_case_missing_required_fields(client, auth_headers):
    response = client.post("/api/cases", json={"patient_id": "PT-1"}, headers=auth_headers)
    assert response.status_code == 422


def test_create_case_blank_fields_rejected(client, auth_headers, new_case_payload):
    new_case_payload["medication"] = "   "
    assert client.post("/api/cases", json=new_case_payload, headers=auth_headers).status_code == 422


def test_invalid_status_rejected(client, auth_headers):
    response = client.put("/api/cases/1/status", json={"status": "Approved by AI"}, headers=auth_headers)
    assert response.status_code == 422


def test_unknown_case_returns_404(client, auth_headers):
    assert client.get("/api/cases/999999", headers=auth_headers).status_code == 404
    assert client.post("/api/cases/999999/analyze", headers=auth_headers).status_code == 404


def test_required_field_cannot_be_cleared(client, auth_headers):
    response = client.put("/api/cases/1", json={"medication": None}, headers=auth_headers)
    assert response.status_code == 422
