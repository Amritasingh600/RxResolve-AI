import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import ThemeToggle from "../components/ThemeToggle.jsx";
import { getToken } from "../services/api.js";

const DEMO_SCENARIOS = [
  {
    id: "pa",
    label: "💊 PA001 · Prior Auth",
    med: "ExampleMed 50 mg",
    payer: "DemoHealth Insurance",
    code: "PA001",
    rawMessage: "Prior authorization required for specialty medication fill.",
    category: "Prior Authorization Required",
    confidence: "95% High Confidence",
    badgeClass: "badge-purple",
    explanation: "The health plan requires prior authorization demonstrating clinical necessity and trial of formulary alternatives before approving coverage.",
    policyMatch: "Policy #PA-2024-01: Specialty drug authorization mandates chart notes confirming diagnosis and prescriber attestation.",
    checklist: ["Confirm clinical diagnosis in chart", "Verify 30-day medical notes", "Attach prescriber justification statement"],
    draftSnippet: "RE: Prior Authorization Request for ExampleMed 50 mg (Patient ID: P-100293)\nDear Medical Review Board, Please find attached documentation..."
  },
  {
    id: "formulary",
    label: "🚫 Code 70 · Non-Formulary",
    med: "Cardiozen 10 mg",
    payer: "MeadowCare Demo Plan",
    code: "Code 70",
    rawMessage: "Product/service not covered - non-formulary medication",
    category: "Drug Not Covered",
    confidence: "98% High Confidence",
    badgeClass: "badge-orange",
    explanation: "Cardiozen 10 mg is excluded from the active drug formulary. A formal formulary exception request is required.",
    policyMatch: "Policy #FORM-EX-04: Non-formulary exception requires evidence that preferred Tier 1 & 2 alternatives were ineffective or contraindicated.",
    checklist: ["Identify preferred formulary alternatives", "Document failure/allergy to formulary drugs", "Submit exception appeal form"],
    draftSnippet: "RE: Formulary Exception Appeal for Cardiozen 10 mg\nCoverage requested due to documented patient intolerance to formulary Tier 1 agents..."
  },
  {
    id: "ql",
    label: "⏳ Code 76 · Quantity Limit",
    med: "Painex ER 20 mg",
    payer: "Summit Sample Health",
    code: "Code 76",
    rawMessage: "Plan limitations exceeded - quantity limit of 60 tablets per 30 days",
    category: "Quantity Limit",
    confidence: "92% High Confidence",
    badgeClass: "badge-blue",
    explanation: "Prescribed dose exceeds the safety quantity limit set by the plan (max 60 tabs/month). Quantity override required.",
    policyMatch: "Policy #QL-882: Doses exceeding standard daily limit require specialist pain management attestation and dosing rationale.",
    checklist: ["Verify prescribed daily frequency", "Confirm specialist prescriber credentials", "Prepare quantity override exception request"],
    draftSnippet: "RE: Quantity Limit Override Request for Painex ER 20 mg\nRequesting override to 90 tablets/30 days based on clinical titration protocol..."
  },
  {
    id: "step",
    label: "🔄 Code 608 · Step Therapy",
    med: "Glucorin XR 500 mg",
    payer: "RiverBend Demo Plan",
    code: "Code 608",
    rawMessage: "Step therapy required: trial of preferred first-line agent on file",
    category: "Step Therapy",
    confidence: "96% High Confidence",
    badgeClass: "badge-teal",
    explanation: "Plan protocol requires trial and failure of generic first-line therapy (Metformin) before Glucorin XR is covered.",
    policyMatch: "Policy #ST-109: Step therapy protocol mandates 30-day pharmacy dispensing record of Step 1 agent prior to approval.",
    checklist: ["Retrieve dispensing history for Step 1 drug", "Document treatment failure or gastrointestinal side effects", "Submit step protocol exception"],
    draftSnippet: "RE: Step Therapy Exemption for Glucorin XR 500 mg\nPatient experienced severe GI intolerance during 4-week trial of first-line Metformin..."
  }
];

export default function LandingPage() {
  const navigate = useNavigate();
  const isAuthenticated = Boolean(getToken());
  const [activeScenario, setActiveScenario] = useState(DEMO_SCENARIOS[0]);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [activeTab, setActiveTab] = useState("analysis"); // "analysis" | "policy" | "pa"

  function handleSelectScenario(scenario) {
    if (scenario.id === activeScenario.id) return;
    setIsAnalyzing(true);
    setActiveScenario(scenario);
    setTimeout(() => {
      setIsAnalyzing(false);
    }, 300);
  }

  return (
    <div className="landing-page">
      {/* Top Navbar */}
      <header className="landing-nav">
        <div className="landing-nav-inner">
          <div className="brand">
            <span className="brand-mark">Rx</span>
            <div>
              <div className="brand-name">RxResolveAI</div>
              <div className="brand-sub">Rejection &amp; PA Decision Support</div>
            </div>
          </div>
          <div className="landing-nav-actions">
            <ThemeToggle className="landing-theme-toggle" />
            {isAuthenticated ? (
              <Link to="/" className="btn btn-primary">
                Open Workspace →
              </Link>
            ) : (
              <Link to="/login" className="btn btn-primary">
                Sign In
              </Link>
            )}
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="landing-hero">
        <div className="landing-hero-content">
          <div className="hero-badge">
            <span className="hero-badge-pulse" />
            <span>AI-Assisted Administrative Guidance</span>
          </div>
          <h1 className="hero-title">
            Resolve Prescription Rejections <span className="hero-highlight">Faster &amp; Smarter</span>
          </h1>
          <p className="hero-subtitle">
            Understand rejection reasons, query local payer policy documents using TF-IDF search,
            and generate prior authorization checklists and draft letters in seconds.
          </p>

          <div className="hero-actions">
            {isAuthenticated ? (
              <Link to="/" className="btn btn-primary btn-lg">
                Go to Workspace ➔
              </Link>
            ) : (
              <Link to="/login" className="btn btn-primary btn-lg">
                Get Started Now ➔
              </Link>
            )}
            <a href="#interactive-demo" className="btn btn-ghost btn-lg">
              Try Live Demo ↓
            </a>
          </div>

          <div className="hero-disclaimer">
            <span className="icon">🛡️</span>
            <span>
              <strong>Administrative Decision Support:</strong> RxResolveAI assists staff workflows. All recommendations require authorized human review.
            </span>
          </div>
        </div>

        {/* Hero Floating Interactive Preview */}
        <div className="hero-preview-wrapper" id="interactive-demo">
          <div className="hero-preview-card">
            <div className="preview-header">
              <div className="preview-dots">
                <span className="dot red" />
                <span className="dot yellow" />
                <span className="dot green" />
              </div>
              <div className="preview-title">Interactive Analysis Sandbox</div>
              <span className="badge badge-teal">Live Demo</span>
            </div>

            <div className="preview-body">
              {/* Preset Selectors */}
              <div className="scenario-selector-label">Select Sample Rejection Scenario:</div>
              <div className="scenario-pills">
                {DEMO_SCENARIOS.map((scen) => (
                  <button
                    key={scen.id}
                    type="button"
                    className={`scenario-pill ${activeScenario.id === scen.id ? "active" : ""}`}
                    onClick={() => handleSelectScenario(scen)}
                  >
                    {scen.label}
                  </button>
                ))}
              </div>

              {/* Rejection Input Preview */}
              <div className="preview-rejection-box">
                <div className="preview-rejection-top">
                  <span className="preview-code-tag">{activeScenario.code}</span>
                  <span className="muted small">{activeScenario.payer}</span>
                </div>
                <div className="preview-code-title">{activeScenario.rawMessage}</div>
                <div className="preview-med-info">Medication: <strong>{activeScenario.med}</strong></div>
              </div>

              {/* Pipeline Stage Indicators */}
              <div className="preview-pipeline">
                <div className={`pipeline-step ${isAnalyzing ? "loading" : "active"}`}>
                  <span className="step-icon">⚡</span>
                  <span>1. Rule Engine</span>
                </div>
                <div className="pipeline-line" />
                <div className={`pipeline-step ${isAnalyzing ? "loading" : "active"}`}>
                  <span className="step-icon">🔍</span>
                  <span>2. Policy Match</span>
                </div>
                <div className="pipeline-line" />
                <div className={`pipeline-step ${isAnalyzing ? "loading" : "active"}`}>
                  <span className="step-icon">📄</span>
                  <span>3. PA Assistant</span>
                </div>
              </div>

              {/* Interactive Output Tabs */}
              <div className="demo-tabs">
                <button
                  className={`demo-tab ${activeTab === "analysis" ? "active" : ""}`}
                  onClick={() => setActiveTab("analysis")}
                >
                  💡 Explanation
                </button>
                <button
                  className={`demo-tab ${activeTab === "policy" ? "active" : ""}`}
                  onClick={() => setActiveTab("policy")}
                >
                  📚 Policy Clause
                </button>
                <button
                  className={`demo-tab ${activeTab === "pa" ? "active" : ""}`}
                  onClick={() => setActiveTab("pa")}
                >
                  📝 PA Checklist &amp; Draft
                </button>
              </div>

              {/* Output Content Card */}
              <div className="preview-result-card">
                {isAnalyzing ? (
                  <div className="demo-analyzing-state">
                    <span className="spinner" />
                    <span>Analyzing rejection code and matching policy documents...</span>
                  </div>
                ) : (
                  <>
                    {activeTab === "analysis" && (
                      <div className="demo-tab-content">
                        <div className="result-tag">
                          <span className={`badge ${activeScenario.badgeClass}`}>{activeScenario.category}</span>
                          <span className="confidence confidence-high">{activeScenario.confidence}</span>
                        </div>
                        <p className="result-text">{activeScenario.explanation}</p>
                        <div className="result-footer">
                          <span className="badge badge-outline">Plain-Language Guidance</span>
                          <span className="muted small">Human Staff Review Required</span>
                        </div>
                      </div>
                    )}

                    {activeTab === "policy" && (
                      <div className="demo-tab-content">
                        <div className="result-tag">
                          <span className="badge badge-blue">TF-IDF Policy Search Result</span>
                          <span className="muted small">Relevance Score: 0.89</span>
                        </div>
                        <div className="quote-box">{activeScenario.policyMatch}</div>
                        <div className="result-footer">
                          <span className="muted small">Source: Local Policy Knowledge Base</span>
                        </div>
                      </div>
                    )}

                    {activeTab === "pa" && (
                      <div className="demo-tab-content">
                        <div className="result-tag">
                          <span className="badge badge-green">Automated Checklist</span>
                          <span className="badge badge-outline">Editable Letter Draft</span>
                        </div>
                        <ul className="demo-checklist">
                          {activeScenario.checklist.map((item, idx) => (
                            <li key={idx}>✓ {item}</li>
                          ))}
                        </ul>
                        <div className="draft-preview-box">
                          <code>{activeScenario.draftSnippet}</code>
                        </div>
                      </div>
                    )}
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section id="how-it-works" className="landing-section">
        <div className="section-header">
          <span className="section-tag">Streamlined Workflow</span>
          <h2>How RxResolveAI Works</h2>
          <p className="section-desc">Four clear steps from rejection receipt to administrative resolution.</p>
        </div>

        <div className="workflow-grid">
          <div className="workflow-card">
            <div className="step-number">01</div>
            <h3>Capture Notice</h3>
            <p>Type rejection details or upload a PDF / DOCX / TXT rejection notice to extract key fields automatically.</p>
          </div>

          <div className="workflow-card">
            <div className="step-number">02</div>
            <h3>AI &amp; Rule Analysis</h3>
            <p>Deterministic rules categorize the code (8 categories) while TF-IDF search identifies matching policy excerpts.</p>
          </div>

          <div className="workflow-card">
            <div className="step-number">03</div>
            <h3>Plain-Language Guidance</h3>
            <p>Receive clear explanations of why the claim was rejected, what information is missing, and the next steps.</p>
          </div>

          <div className="workflow-card">
            <div className="step-number">04</div>
            <h3>PA Assistance &amp; Review</h3>
            <p>Generate PA checklists and pre-filled letter drafts. Staff reviews, edits, and tracks case completion.</p>
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="landing-section bg-alt">
        <div className="section-header">
          <span className="section-tag">Core Capabilities</span>
          <h2>Designed for Healthcare &amp; Pharmacy Staff</h2>
          <p className="section-desc">Built with practical tools to simplify daily claim rejection management.</p>
        </div>

        <div className="features-grid">
          <div className="feature-card">
            <div className="feature-icon">🎯</div>
            <h3>8-Category Classification</h3>
            <p>Instant classification across PA, Non-Formulary, Quantity Limits, Refill Too Soon, Step Therapy, and more.</p>
          </div>

          <div className="feature-card">
            <div className="feature-icon">📚</div>
            <h3>Policy Knowledge Base Search</h3>
            <p>Local TF-IDF search ranks matching policy documents and highlights exact clinical requirement clauses.</p>
          </div>

          <div className="feature-card">
            <div className="feature-icon">📄</div>
            <h3>Document Field Extraction</h3>
            <p>Upload rejection letters to pre-fill patient ID, claim ID, prescriber ID, medication, and payer details.</p>
          </div>

          <div className="feature-card">
            <div className="feature-icon">📝</div>
            <h3>PA Checklist &amp; Draft Builder</h3>
            <p>Automatically populates prior authorization checklists and editable request letters ready for review.</p>
          </div>

          <div className="feature-card">
            <div className="feature-icon">📊</div>
            <h3>Status Audit History</h3>
            <p>Track cases through New, Under Review, PA Required, Submitted, and Resolved with full history logging.</p>
          </div>

          <div className="feature-card">
            <div className="feature-icon">🔒</div>
            <h3>Local &amp; Secure Architecture</h3>
            <p>Runs entirely on local infrastructure with optional local LLM integration (Ollama). Zero external data leaks.</p>
          </div>
        </div>
      </section>

      {/* Human-in-the-Loop Governance Callout */}
      <section className="landing-section">
        <div className="governance-card">
          <div className="governance-icon">⚖️</div>
          <div className="governance-content">
            <h3>Human-in-the-Loop Governance</h3>
            <p>
              RxResolveAI is an administrative decision support tool. It does not replace medical judgment, submit insurance claims directly, or make clinical treatment decisions. Authorized human staff must review and verify all generated checklists and draft letters before submission.
            </p>
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="landing-cta">
        <h2>Ready to Simplify Claim Rejection Workflows?</h2>
        <p>Log in with demo accounts to experience AI-assisted resolution in action.</p>
        <div className="cta-actions">
          <Link to="/login" className="btn btn-primary btn-lg">
            Sign In to RxResolveAI ➔
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="landing-footer">
        <div className="footer-inner">
          <div className="footer-brand">
            <span className="brand-mark">Rx</span>
            <span>RxResolveAI</span>
          </div>
          <p className="footer-text">
            Local Administrative Decision Support System · Fictional Demo Environment
          </p>
        </div>
      </footer>
    </div>
  );
}
