import ai_service
from ai_service import analyze_case, check_ollama


CASE = {
    "patient_id": "PT-1",
    "claim_id": "RX-1",
    "medication": "ExampleMed",
    "insurance": "DemoHealth",
    "rejection_code": "PA001",
    "rejection_message": "Prior authorization required",
}


def test_disabled_ollama_uses_rule_based(monkeypatch):
    monkeypatch.setattr(ai_service.config, "USE_OLLAMA", False)
    ai_service.reset_status_cache()
    status = check_ollama(force=True)
    assert status["available"] is False
    assert status["mode"] == "rule-based"

    result = analyze_case(CASE)
    assert result["analysis_source"] == "rule-based"
    assert result["category"] == "Prior Authorization Required"
    assert result["next_steps"]


def test_unreachable_ollama_falls_back(monkeypatch):
    # Enable Ollama but point it at a port where nothing is running.
    monkeypatch.setattr(ai_service.config, "USE_OLLAMA", True)
    monkeypatch.setattr(ai_service.config, "OLLAMA_URL", "http://127.0.0.1:9")
    ai_service.reset_status_cache()

    assert check_ollama(force=True)["available"] is False
    assert ai_service.generate_text("hello") is None
    result = analyze_case(CASE)
    assert result["analysis_source"] == "rule-based"
    ai_service.reset_status_cache()


def test_llm_failure_mid_request_keeps_template(monkeypatch):
    # Ollama "available" but generation fails -> template text is used.
    monkeypatch.setattr(ai_service, "is_ollama_available", lambda: True)
    monkeypatch.setattr(ai_service, "generate_text", lambda prompt: None)
    result = analyze_case(CASE)
    assert result["analysis_source"] == "rule-based"
    assert "prior authorization" in result["explanation"].lower()


def test_llm_text_is_used_when_available(monkeypatch):
    monkeypatch.setattr(ai_service, "is_ollama_available", lambda: True)
    monkeypatch.setattr(ai_service, "generate_text", lambda prompt: "Plain language explanation.")
    result = analyze_case(CASE)
    assert result["explanation"] == "Plain language explanation."
    assert result["analysis_source"].startswith("ollama")
    # The category still comes from the rules, not from the LLM.
    assert result["category"] == "Prior Authorization Required"


def test_llm_category_suggestion_must_be_a_known_category(monkeypatch):
    monkeypatch.setattr(ai_service, "is_ollama_available", lambda: True)
    monkeypatch.setattr(ai_service, "generate_text", lambda prompt: "Approved! The drug is fine.")
    result = analyze_case({**CASE, "rejection_code": "", "rejection_message": "Contact help desk"})
    assert result["category"] == "Other"
    assert "manual review required" in result["missing_info"][0]
