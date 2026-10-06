import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { CategoryBadge, StatusBadge } from "../components/Badges.jsx";
import CaseTable from "../components/CaseTable.jsx";
import { Alert, EmptyState, Loading } from "../components/Feedback.jsx";
import StatusChanger from "../components/StatusChanger.jsx";
import { api } from "../services/api.js";
import { formatDateTime, isPaCase } from "../utils/format.js";

// Categories where an exception request is often prepared (similar workflow to PA).
const EXCEPTION_CATEGORIES = ["Step Therapy", "Quantity Limit", "Drug Not Covered"];

export default function PriorAuthPage() {
  const { id } = useParams();
  return id ? <PaAssistant caseId={id} /> : <PaCaseList />;
}

// ------------------------------------------------------------ case list ---
function PaCaseList() {
  const navigate = useNavigate();
  const [cases, setCases] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.getCases().then(setCases).catch((err) => setError(err.message));
  }, []);

  if (error) return <Alert>{error}</Alert>;
  if (!cases) return <Loading />;

  const open = cases.filter((c) => c.status !== "Resolved");
  const paCases = open.filter(isPaCase);
  const exceptionCases = open.filter((c) => !isPaCase(c) && EXCEPTION_CATEGORIES.includes(c.category));

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Prior Authorization Assistant</h1>
          <p className="muted">Build a PA checklist and a draft request for staff to review. Nothing is sent to any payer.</p>
        </div>
        <select className="case-picker" defaultValue="" onChange={(e) => e.target.value && navigate(`/pa/${e.target.value}`)}>
          <option value="">Open any case…</option>
          {cases.map((c) => (
            <option key={c.id} value={c.id}>
              #{c.id} · {c.medication} · {c.patient_id}
            </option>
          ))}
        </select>
      </div>

      <section className="card">
        <h2>Open cases requiring prior authorization</h2>
        {paCases.length === 0 ? (
          <EmptyState title="No open PA cases">Cases classified as "Prior Authorization Required" appear here.</EmptyState>
        ) : (
          <CaseTable cases={paCases} linkPrefix="/pa" />
        )}
      </section>

      <section className="card">
        <h2>Cases that may need an exception request</h2>
        <p className="muted small">Step therapy, quantity limit and non-formulary rejections often use a similar request process.</p>
        {exceptionCases.length === 0 ? <p className="muted">None.</p> : <CaseTable cases={exceptionCases} linkPrefix="/pa" />}
      </section>
    </div>
  );
}

// --------------------------------------------------------- one case -------
function PaAssistant({ caseId }) {
  const [caseData, setCaseData] = useState(null);
  const [checklist, setChecklist] = useState([]);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState("");

  function applyCase(data) {
    setCaseData(data);
    setChecklist(data.pa_checklist || []);
    setDraft(data.pa_draft || "");
  }

  useEffect(() => {
    setCaseData(null);
    api.getCase(caseId).then(applyCase).catch((err) => setError(err.message));
  }, [caseId]);

  async function run(label, action, successMessage) {
    setBusy(label);
    setError("");
    setMessage("");
    try {
      applyCase(await action());
      if (successMessage) setMessage(successMessage);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy("");
    }
  }

  function toggleItem(key) {
    setChecklist(checklist.map((item) => (item.key === key && !item.auto ? { ...item, done: !item.done } : item)));
  }

  function downloadDraft() {
    const blob = new Blob([draft], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `case-${caseId}-draft.txt`;
    link.click();
    URL.revokeObjectURL(url);
  }

  async function copyDraft() {
    try {
      await navigator.clipboard.writeText(draft);
      setMessage("Draft copied to clipboard.");
    } catch {
      setError("Could not copy automatically. Select the text and copy it manually.");
    }
  }

  if (error && !caseData) return <Alert>{error}</Alert>;
  if (!caseData) return <Loading />;

  const missing = checklist.filter((item) => !item.done);
  const checklistChanged = JSON.stringify(checklist) !== JSON.stringify(caseData.pa_checklist || []);
  const draftChanged = draft !== (caseData.pa_draft || "");
  const notPa = caseData.category && caseData.category !== "Prior Authorization Required";

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <div className="breadcrumb">
            <Link to="/pa">Prior Authorization</Link> / Case #{caseData.id}
          </div>
          <h1>PA Assistant · {caseData.medication}</h1>
          <div className="header-badges">
            <StatusBadge status={caseData.status} />
            <CategoryBadge category={caseData.category} />
            <span className="muted small">
              {caseData.patient_id} · {caseData.insurance} · code {caseData.rejection_code || "—"}
            </span>
          </div>
        </div>
        <Link to={`/cases/${caseData.id}`} className="btn btn-ghost">
          ← Case details
        </Link>
      </div>

      <Alert onClose={() => setError("")}>{error}</Alert>
      <Alert type="success" onClose={() => setMessage("")}>
        {message}
      </Alert>

      {notPa && (
        <div className="alert alert-info">
          <span>
            This case is classified as <strong>{caseData.category}</strong>, not "Prior Authorization Required". You can
            still prepare a draft (for example an exception request) if staff decide it is appropriate.
          </span>
        </div>
      )}

      <div className="grid-2 pa-grid">
        <section className="card">
          <h2>Prior authorization checklist</h2>
          {!caseData.category ? (
            <>
              <p className="muted">Analyze the case first to build the checklist.</p>
              <button
                className="btn btn-primary"
                disabled={!!busy}
                onClick={() => run("analyze", () => api.analyzeCase(caseId), "Case analyzed. Checklist created.")}
              >
                {busy === "analyze" ? "Analyzing…" : "Analyze Rejection"}
              </button>
            </>
          ) : (
            <>
              <ul className="checklist">
                {checklist.map((item) => (
                  <li key={item.key} className={item.done ? "done" : ""}>
                    <label>
                      <input type="checkbox" checked={item.done} disabled={item.auto} onChange={() => toggleItem(item.key)} />
                      <span>
                        {item.label}
                        {item.auto && <span className="tag">auto</span>}
                        <span className="hint">{item.hint}</span>
                      </span>
                    </label>
                  </li>
                ))}
              </ul>
              <div className={`next-step ${missing.length ? "" : "complete"}`}>
                <strong>Next step: </strong>
                {missing.length
                  ? `Review the missing information before submitting the request (${missing.length} item${missing.length > 1 ? "s" : ""} open).`
                  : "All items complete. An authorized staff member can submit the request through the payer's official process."}
              </div>
              <p className="muted small">
                "auto" items are checked from the case data — edit the case to complete them. Other items are confirmed by
                staff.
              </p>
              <button
                className="btn btn-primary"
                disabled={!checklistChanged || !!busy}
                onClick={() => run("checklist", () => api.updateChecklist(caseId, checklist), "Checklist saved.")}
              >
                {busy === "checklist" ? "Saving…" : "Save checklist"}
              </button>
            </>
          )}
        </section>

        <section className="card">
          <div className="card-header">
            <h2>Draft request</h2>
            <span className="badge badge-orange">AI-generated draft — requires human review</span>
          </div>
          <p className="muted small">
            The draft uses only the case data and the local sample policies. Bracketed fields must be completed by staff
            or the prescriber. RxResolveAI never submits requests to insurers.
          </p>
          <div className="draft-actions">
            <button
              className="btn btn-primary"
              disabled={!!busy}
              onClick={() => {
                if (draft && !window.confirm("Replace the current draft with a newly generated one?")) return;
                run("draft", () => api.generatePaDraft(caseId), "Draft generated. Review it carefully before use.");
              }}
            >
              {busy === "draft" ? "Generating…" : draft ? "Regenerate draft" : "Generate checklist & draft"}
            </button>
            {draft && (
              <>
                <button
                  className="btn btn-secondary"
                  disabled={!draftChanged || !!busy}
                  onClick={() => run("save", () => api.savePaDraft(caseId, draft), "Draft changes saved.")}
                >
                  {busy === "save" ? "Saving…" : "Save edits"}
                </button>
                <button className="btn btn-ghost" onClick={copyDraft}>
                  Copy
                </button>
                <button className="btn btn-ghost" onClick={downloadDraft}>
                  Download .txt
                </button>
              </>
            )}
          </div>
          {draft ? (
            <>
              <textarea className="draft-editor" value={draft} onChange={(e) => setDraft(e.target.value)} spellCheck />
              <div className="muted small">
                Generated {formatDateTime(caseData.pa_draft_generated_at)} · source: {caseData.pa_draft_source}
              </div>
            </>
          ) : (
            <EmptyState title="No draft yet">Click "Generate checklist & draft" to create one.</EmptyState>
          )}
        </section>
      </div>

      <section className="card">
        <h2>Review &amp; update case status</h2>
        <p className="muted small">
          After staff have reviewed the draft and submitted it through the payer's official channel themselves, record it
          here (e.g. "Submitted").
        </p>
        <StatusChanger
          key={caseData.status}
          caseData={caseData}
          onUpdated={(updated) => {
            applyCase(updated);
            setMessage(`Status changed to "${updated.status}".`);
          }}
          onError={setError}
        />
      </section>
    </div>
  );
}
