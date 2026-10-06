from pathlib import Path

import policy_search
from policy_search import PolicyIndex, list_policies, read_policy, search_policies, tokenize


def test_tokenize_removes_stopwords_and_punctuation():
    assert tokenize("The Prior-Authorization is REQUIRED!") == ["prior", "authorization", "required"]


def test_prior_authorization_query_finds_pa_policy():
    results = search_policies("Prior Authorization Required ExampleMed DemoHealth")
    assert results
    assert results[0]["source"] == "prior_authorization.txt"
    assert results[0]["score"] > 0


def test_quantity_query_finds_quantity_policy():
    results = search_policies("quantity limit exceeded Painex ER")
    assert results[0]["source"] == "quantity_limit.txt"


def test_empty_query_returns_nothing():
    assert search_policies("") == []


def test_missing_policy_folder_does_not_crash(tmp_path):
    index = PolicyIndex(tmp_path / "does_not_exist")
    assert index.search("prior authorization") == []


def test_list_and_read_policies():
    names = [p["filename"] for p in list_policies()]
    assert "step_therapy.txt" in names
    policy = read_policy("step_therapy.txt")
    assert "Step Therapy" in policy["title"]


def test_read_policy_blocks_path_traversal():
    assert read_policy("../backend/config.py") is None
    assert read_policy("..\\README.md") is None


def test_index_picks_up_new_files(tmp_path, monkeypatch):
    monkeypatch.setattr(policy_search.config, "POLICY_DIR", tmp_path)
    Path(tmp_path, "custom.txt").write_text("Title: Custom\n\nZebracillin requires a special form.", encoding="utf-8")
    results = search_policies("zebracillin")
    assert results and results[0]["source"] == "custom.txt"
