import { ConfidenceBadge } from "./Badges.jsx";
import { formatDateTime } from "../utils/format.js";

// The "Explain the rejection" section of the case details page.
export default function AnalysisPanel({ caseData, onAnalyze, analyzing }) {
  if (!caseData.category) {
    return (
      <section className="card analysis-empty">
        <h2>AI analysis</h2>
        <p className="muted">This case has not been analyzed yet.</p>
        <button className="btn btn-primary" onClick={onAnalyze} disabled={analyzing}>
          {analyzing ? "Analyzing…" : "Analyze Rejection"}
        </button>
      </section>
    );
  }

  const insufficient = caseData.category === "Other";

  return (
    <section className="card analysis">
      <div className="card-header">
        <h2>AI analysis — explanation</h2>
        <span className="badge badge-yellow">Pending human review</span>
      </div>

      <div className="analysis-summary">
        <div>
          <div className="label">Category</div>
          <div className="value">{caseData.category}</div>
        </div>
        <div>
          <div className="label">Confidence</div>
          <div className="value">
            <ConfidenceBadge confidence={caseData.confidence} />
          </div>
        </div>
        <div>
          <div className="label">Analysis method</div>
          <div className="value small">{caseData.analysis_source}</div>
        </div>
      </div>

      {insufficient && (
        <div className="alert alert-warning">
          <span>Insufficient information — manual review required.</span>
        </div>
      )}

      <div className="explain-grid">
        <div>
          <h3>What happened?</h3>
          <p className="pre-line">{caseData.explanation}</p>

          <h3>Possible reason</h3>
          <p>{caseData.possible_reason}</p>

          <h3>Why this category?</h3>
          <p className="muted">{caseData.classification_reason}</p>
        </div>
        <div>
          <h3>Suggested next step</h3>
          <p className="suggested">{caseData.suggested_action}</p>

          <h3>What should staff do?</h3>
          <ol className="steps">
            {(caseData.next_steps || []).map((step, index) => (
              <li key={index}>{step}</li>
            ))}
          </ol>

          {caseData.missing_info?.length > 0 && (
            <>
              <h3>Information that may be missing</h3>
              <ul className="missing">
                {caseData.missing_info.map((item, index) => (
                  <li key={index}>{item}</li>
                ))}
              </ul>
            </>
          )}
        </div>
      </div>
      <p className="muted small">
        Analyzed {formatDateTime(caseData.analyzed_at)}. This is administrative guidance only — the final decision stays
        with authorized staff.
      </p>
    </section>
  );
}
