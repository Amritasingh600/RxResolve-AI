import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { CategoryBadge, ConfidenceBadge, StatusBadge } from "../components/Badges.jsx";
import CaseForm, { caseToForm, validateCase } from "../components/CaseForm.jsx";
import { Alert, Loading } from "../components/Feedback.jsx";
import FileUpload from "../components/FileUpload.jsx";
import StatusChanger from "../components/StatusChanger.jsx";
import AnalysisPanel from "../components/AnalysisPanel.jsx";
import { api } from "../services/api.js";
import { formatDate, formatDateTime } from "../utils/format.js";

const OPTIONAL_FIELDS = ["quantity", "date_of_service", "prescriber", "notes"];

export default function CaseDetailsPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [caseData, setCaseData] = useState(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [analyzing, setAnalyzing] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState(null);
  const [formErrors, setFormErrors] = useState({});
  const [openDocument, setOpenDocument] = useState(null);

  useEffect(() => {
    setCaseData(null);
    setError("");
    api.getCase(id).then(setCaseData).catch((err) => setError(err.message));
  }, [id]);

  async function runAction(action, successMessage) {
    setError("");
    setMessage("");
    try {
      setCaseData(await action());
      if (successMessage) setMessage(successMessage);
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleAnalyze() {
    setAnalyzing(true);
    await runAction(() => api.analyzeCase(id), "Analysis complete. Please review the results below.");
    setAnalyzing(false);
  }

  async function handleUpload(file) {
    setUploading(true);
    await runAction(async () => {
      await api.uploadDocument(file, id);
      return api.getCase(id);
    }, "Document uploaded and linked to this case.");
    setUploading(false);
  }

  async function toggleDocument(documentId) {
    if (openDocument?.id === documentId) {
      setOpenDocument(null);
      return;
    }
    try {
      setOpenDocument(await api.getDocument(documentId));
    } catch (err) {
      setError(err.message);
    }
  }

  function startEditing() {
    setForm(caseToForm(caseData));
    setFormErrors({});
    setEditing(true);
  }

  async function saveEdits(event) {
    event.preventDefault();
    const validationErrors = validateCase(form);
    setFormErrors(validationErrors);
    if (Object.keys(validationErrors).length > 0) return;

    const payload = { ...form };
    OPTIONAL_FIELDS.forEach((key) => {
      if (payload[key] === "") payload[key] = null;
    });
    await runAction(() => api.updateCase(id, payload), "Case updated. Run the analysis again if the rejection changed.");
    setEditing(false);
  }

  async function handleDelete() {
    if (!window.confirm(`Delete case #${id}? This cannot be undone.`)) return;
    try {
      await api.deleteCase(id);
      navigate("/cases");
    } catch (err) {
      setError(err.message);
    }
  }

  if (error && !caseData) return <Alert>{error}</Alert>;
  if (!caseData) return <Loading />;

  const checklist = caseData.pa_checklist || [];
  const checklistDone = checklist.filter((item) => item.done).length;

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <div className="breadcrumb">
            <Link to="/cases">Cases</Link> / #{caseData.id}
          </div>
          <h1>
            Case #{caseData.id} · {caseData.medication}
          </h1>
          <div className="header-badges">
            <StatusBadge status={caseData.status} />
            <CategoryBadge category={caseData.category} />
          </div>
        </div>
        <div className="actions">
          <button className="btn btn-primary" onClick={handleAnalyze} disabled={analyzing}>
            {analyzing ? "Analyzing…" : caseData.category ? "Re-analyze rejection" : "Analyze Rejection"}
          </button>
          <Link to={`/pa/${caseData.id}`} className="btn btn-secondary">
            Open PA Assistant
          </Link>
        </div>
      </div>

      <Alert onClose={() => setError("")}>{error}</Alert>
      <Alert type="success" onClose={() => setMessage("")}>
        {message}
      </Alert>

      <div className="grid-2">
        <section className="card">
          <div className="card-header">
            <h2>Patient / case information</h2>
            {!editing && (
              <button className="btn btn-ghost btn-sm" onClick={startEditing}>
                Edit
              </button>
            )}
          </div>
          {editing ? (
            <form onSubmit={saveEdits} noValidate>
              <CaseForm form={form} setForm={setForm} errors={formErrors} />
              <div className="form-actions">
                <button type="button" className="btn btn-ghost" onClick={() => setEditing(false)}>
                  Cancel
                </button>
                <button className="btn btn-primary">Save changes</button>
              </div>
            </form>
          ) : (
            <dl className="details">
              <div><dt>Patient ID</dt><dd>{caseData.patient_id}</dd></div>
              <div><dt>Claim / Rx ID</dt><dd>{caseData.claim_id}</dd></div>
              <div><dt>Medication</dt><dd>{caseData.medication}</dd></div>
              <div><dt>Insurance</dt><dd>{caseData.insurance}</dd></div>
              <div><dt>Quantity</dt><dd>{caseData.quantity || "—"}</dd></div>
              <div><dt>Date of service</dt><dd>{formatDate(caseData.date_of_service)}</dd></div>
              <div><dt>Prescriber</dt><dd>{caseData.prescriber || "—"}</dd></div>
              <div><dt>Created</dt><dd>{formatDateTime(caseData.created_at)} by {caseData.created_by || "—"}</dd></div>
              {caseData.notes && <div className="span-2"><dt>Notes</dt><dd className="pre-line">{caseData.notes}</dd></div>}
            </dl>
          )}
        </section>

        <section className="card">
          <h2>Rejection</h2>
          <dl className="details">
            <div><dt>Rejection code</dt><dd><code>{caseData.rejection_code || "—"}</code></dd></div>
            <div><dt>Classification</dt><dd><CategoryBadge category={caseData.category} /></dd></div>
            <div className="span-2">
              <dt>Original rejection message</dt>
              <dd className="quote">{caseData.rejection_message}</dd>
            </div>
          </dl>
        </section>
      </div>

      <AnalysisPanel caseData={caseData} onAnalyze={handleAnalyze} analyzing={analyzing} />

      <section className="card">
        <h2>Policy information</h2>
        {!caseData.category ? (
          <p className="muted">Analyze the case to search the policy knowledge base.</p>
        ) : caseData.policy_matches?.length ? (
          <div className="policy-matches">
            {caseData.policy_matches.map((match, index) => (
              <div key={index} className="policy-match">
                <div className="policy-match-header">
                  <strong>{match.title}</strong>
                  <span className="muted small">
                    Source: <Link to={`/policies?file=${encodeURIComponent(match.source)}`}>{match.source}</Link> · relevance{" "}
                    {Math.round(match.score * 100)}%
                  </span>
                </div>
                <p className="pre-line">{match.excerpt}</p>
              </div>
            ))}
            <p className="muted small">Excerpts come from the local sample policy documents (fictional). Always confirm with the payer.</p>
          </div>
        ) : (
          <p className="muted">No relevant policy was found in the local knowledge base. Confirm the requirements with the payer.</p>
        )}
      </section>

      <div className="grid-2">
        <section className="card">
          <div className="card-header">
            <h2>Prior authorization</h2>
            <Link to={`/pa/${caseData.id}`}>Open PA Assistant →</Link>
          </div>
          {checklist.length > 0 ? (
            <p>
              Checklist: <strong>{checklistDone} of {checklist.length}</strong> items complete.
            </p>
          ) : (
            <p className="muted">The checklist is created when the case is analyzed.</p>
          )}
          {caseData.pa_draft ? (
            <p>
              Draft generated {formatDateTime(caseData.pa_draft_generated_at)} ({caseData.pa_draft_source}).{" "}
              <span className="badge badge-orange">AI-generated draft — requires human review</span>
            </p>
          ) : (
            <p className="muted">No draft generated yet.</p>
          )}
        </section>

        <section className="card">
          <h2>Documents</h2>
          {caseData.documents.length === 0 && <p className="muted">No documents linked to this case.</p>}
          <ul className="doc-list">
            {caseData.documents.map((doc) => (
              <li key={doc.id}>
                <button className="link-button" onClick={() => toggleDocument(doc.id)}>
                  {doc.filename}
                </button>
                <span className="muted small">
                  {doc.file_type.toUpperCase()} · {formatDateTime(doc.uploaded_at)}
                </span>
                {openDocument?.id === doc.id && <pre className="text-preview">{openDocument.content}</pre>}
              </li>
            ))}
          </ul>
          <FileUpload label="Attach document" onUpload={handleUpload} busy={uploading} />
        </section>
      </div>

      <section className="card">
        <h2>Case status</h2>
        <StatusChanger
          key={caseData.status}
          caseData={caseData}
          onUpdated={(updated) => {
            setCaseData(updated);
            setMessage(`Status changed to "${updated.status}".`);
          }}
          onError={setError}
        />
        <h3>Status history</h3>
        <ol className="timeline">
          {caseData.history.map((entry, index) => (
            <li key={index}>
              <div>
                {entry.old_status ? (
                  <>
                    <StatusBadge status={entry.old_status} /> → <StatusBadge status={entry.new_status} />
                  </>
                ) : (
                  <StatusBadge status={entry.new_status} />
                )}
              </div>
              <div className="muted small">
                {formatDateTime(entry.changed_at)} · {entry.changed_by || "—"}
                {entry.note && ` · ${entry.note}`}
              </div>
            </li>
          ))}
        </ol>
      </section>

      <div className="danger-zone">
        <button className="btn btn-danger btn-sm" onClick={handleDelete}>
          Delete case
        </button>
      </div>
    </div>
  );
}
