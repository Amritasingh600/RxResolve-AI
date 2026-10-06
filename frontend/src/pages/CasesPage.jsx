import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import CaseTable from "../components/CaseTable.jsx";
import { Alert, EmptyState, Loading } from "../components/Feedback.jsx";
import { api, CASE_STATUSES, CATEGORIES } from "../services/api.js";

export default function CasesPage() {
  // Filters live in the URL (?q=...&status=...) so they survive a page refresh.
  const [searchParams, setSearchParams] = useSearchParams();
  const q = searchParams.get("q") || "";
  const status = searchParams.get("status") || "";
  const category = searchParams.get("category") || "";

  const [searchText, setSearchText] = useState(q);
  const [cases, setCases] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    setCases(null);
    setError("");
    api
      .getCases({ q, status, category })
      .then(setCases)
      .catch((err) => setError(err.message));
  }, [q, status, category]);

  function updateFilter(key, value) {
    const next = new URLSearchParams(searchParams);
    if (value) next.set(key, value);
    else next.delete(key);
    setSearchParams(next);
  }

  function handleSearch(event) {
    event.preventDefault();
    updateFilter("q", searchText.trim());
  }

  function clearFilters() {
    setSearchText("");
    setSearchParams({});
  }

  const hasFilters = q || status || category;

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Cases</h1>
          <p className="muted">Search and filter rejection cases.</p>
        </div>
        <Link to="/cases/new" className="btn btn-primary">
          + New case
        </Link>
      </div>

      <form className="card filter-bar" onSubmit={handleSearch}>
        <input
          type="search"
          placeholder="Search patient ID, case #, claim ID, medication, insurance…"
          value={searchText}
          maxLength={100}
          onChange={(e) => setSearchText(e.target.value)}
        />
        <select value={status} onChange={(e) => updateFilter("status", e.target.value)} aria-label="Filter by status">
          <option value="">All statuses</option>
          {CASE_STATUSES.map((s) => (
            <option key={s}>{s}</option>
          ))}
        </select>
        <select value={category} onChange={(e) => updateFilter("category", e.target.value)} aria-label="Filter by category">
          <option value="">All categories</option>
          {CATEGORIES.map((c) => (
            <option key={c}>{c}</option>
          ))}
        </select>
        <button className="btn btn-primary">Search</button>
        {hasFilters && (
          <button type="button" className="btn btn-ghost" onClick={clearFilters}>
            Clear
          </button>
        )}
      </form>

      <Alert>{error}</Alert>
      {!cases && !error && <Loading />}
      {cases && (
        <section className="card">
          <div className="muted small table-count">
            {cases.length} case{cases.length === 1 ? "" : "s"}
          </div>
          {cases.length === 0 ? (
            <EmptyState title="No cases found">
              {hasFilters ? "Try different search terms or clear the filters." : <Link to="/cases/new">Create a case</Link>}
            </EmptyState>
          ) : (
            <CaseTable cases={cases} />
          )}
        </section>
      )}
    </div>
  );
}
