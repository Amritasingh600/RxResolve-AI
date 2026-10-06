import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Alert, EmptyState, Loading } from "../components/Feedback.jsx";
import FileUpload from "../components/FileUpload.jsx";
import { api } from "../services/api.js";

export default function PolicyDocumentsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const selectedFile = searchParams.get("file");

  const [policies, setPolicies] = useState(null);
  const [selected, setSelected] = useState(null);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [uploading, setUploading] = useState(false);

  function loadPolicies() {
    return api.getPolicies().then(setPolicies).catch((err) => setError(err.message));
  }

  useEffect(() => {
    loadPolicies();
  }, []);

  // Open the policy named in the URL (?file=...), or the first one.
  useEffect(() => {
    if (!policies || policies.length === 0) return;
    const filename = selectedFile || policies[0].filename;
    api
      .getPolicy(filename)
      .then(setSelected)
      .catch((err) => setError(err.message));
  }, [policies, selectedFile]);

  async function handleSearch(event) {
    event.preventDefault();
    if (!query.trim()) return;
    setError("");
    try {
      setResults(await api.searchPolicies(query.trim()));
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleUpload(file) {
    setUploading(true);
    setError("");
    setMessage("");
    try {
      const added = await api.uploadPolicy(file);
      await loadPolicies();
      setSearchParams({ file: added.filename });
      setMessage(`Added "${added.filename}" to the knowledge base.`);
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Policy documents</h1>
          <p className="muted">
            Local knowledge base used by the analysis. All documents are <strong>fictional samples</strong> for
            demonstration — not real payer policies.
          </p>
        </div>
      </div>

      <Alert onClose={() => setError("")}>{error}</Alert>
      <Alert type="success" onClose={() => setMessage("")}>
        {message}
      </Alert>

      <section className="card">
        <h2>Search policies</h2>
        <form className="filter-bar plain" onSubmit={handleSearch}>
          <input
            type="search"
            placeholder="e.g. quantity limit inhaler, step therapy exception…"
            value={query}
            maxLength={300}
            onChange={(e) => setQuery(e.target.value)}
          />
          <button className="btn btn-primary">Search</button>
        </form>
        {results && results.length === 0 && <p className="muted">No matching policy text found.</p>}
        {results && results.length > 0 && (
          <div className="policy-matches">
            {results.map((match, index) => (
              <div key={index} className="policy-match">
                <div className="policy-match-header">
                  <button className="link-button" onClick={() => setSearchParams({ file: match.source })}>
                    {match.title}
                  </button>
                  <span className="muted small">
                    {match.source} · relevance {Math.round(match.score * 100)}%
                  </span>
                </div>
                <p className="pre-line">{match.excerpt}</p>
              </div>
            ))}
          </div>
        )}
      </section>

      <div className="policy-layout">
        <section className="card policy-list">
          <h2>Documents</h2>
          {!policies && <Loading />}
          {policies && policies.length === 0 && <EmptyState title="No policy documents found" />}
          <ul>
            {policies?.map((policy) => (
              <li key={policy.filename}>
                <button
                  className={`policy-item ${selected?.filename === policy.filename ? "active" : ""}`}
                  onClick={() => setSearchParams({ file: policy.filename })}
                >
                  <span>{policy.title}</span>
                  <span className="muted small">{policy.filename}</span>
                </button>
              </li>
            ))}
          </ul>
          <div className="policy-upload">
            <FileUpload label="Add sample policy" onUpload={handleUpload} busy={uploading} />
            <p className="muted small">Only add fictional or openly licensed sample documents.</p>
          </div>
        </section>

        <section className="card policy-viewer">
          {selected ? (
            <>
              <h2>{selected.title}</h2>
              <div className="muted small">{selected.filename}</div>
              <pre className="policy-text">{selected.content}</pre>
            </>
          ) : (
            <p className="muted">Select a document to read it.</p>
          )}
        </section>
      </div>
    </div>
  );
}
