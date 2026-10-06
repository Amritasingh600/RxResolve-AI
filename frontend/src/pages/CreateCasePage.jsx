import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Alert } from "../components/Feedback.jsx";
import FileUpload from "../components/FileUpload.jsx";
import CaseForm, { EMPTY_CASE, validateCase } from "../components/CaseForm.jsx";
import { api } from "../services/api.js";

// Example values from the project's demo script. All fictional.
const DEMO_EXAMPLE = {
  patient_id: "PT-DEMO-01",
  claim_id: "RX-DEMO-01",
  medication: "ExampleMed",
  insurance: "DemoHealth",
  rejection_code: "PA001",
  rejection_message: "Prior authorization required",
  quantity: "30",
  date_of_service: new Date().toISOString().slice(0, 10),
  prescriber: "",
  notes: "Demo case entered during presentation (fictional).",
};

export default function CreateCasePage() {
  const navigate = useNavigate();
  const [form, setForm] = useState(EMPTY_CASE);
  const [errors, setErrors] = useState({});
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const [upload, setUpload] = useState(null); // response from /api/upload
  const [uploading, setUploading] = useState(false);

  async function handleUpload(file) {
    setUploading(true);
    setError("");
    try {
      setUpload(await api.uploadDocument(file));
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  }

  function applyExtractedFields() {
    const extracted = upload.extracted_fields;
    const next = { ...form };
    Object.keys(EMPTY_CASE).forEach((key) => {
      if (extracted[key]) next[key] = extracted[key];
    });
    setForm(next);
    setErrors({});
  }

  async function handleSubmit(event) {
    event.preventDefault();
    const validationErrors = validateCase(form);
    setErrors(validationErrors);
    if (Object.keys(validationErrors).length > 0) {
      setError("Please fill in the required fields.");
      return;
    }

    setSaving(true);
    setError("");
    try {
      const payload = { ...form, date_of_service: form.date_of_service || null, document_id: upload?.document.id ?? null };
      const created = await api.createCase(payload);
      navigate(`/cases/${created.id}`);
    } catch (err) {
      setError(err.message);
      setSaving(false);
    }
  }

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Create new case</h1>
          <p className="muted">Enter a rejected prescription / claim, or start from an uploaded rejection document.</p>
        </div>
        <button type="button" className="btn btn-ghost" onClick={() => setForm(DEMO_EXAMPLE)}>
          Fill demo example
        </button>
      </div>

      <section className="card">
        <h2>Option A — Upload a rejection document</h2>
        <p className="muted small">
          RxResolveAI extracts the text and looks for fields such as "Patient ID:", "Medication:" and "Rejection Code:".
          Sample files are in the <code>sample_data/</code> folder.
        </p>
        <FileUpload label="Choose rejection document" onUpload={handleUpload} busy={uploading} />

        {upload && (
          <div className="extract-result">
            <div className="extract-header">
              <div>
                <strong>{upload.document.filename}</strong> uploaded · suggested category:{" "}
                <span className="badge badge-outline">{upload.suggested_category}</span>
              </div>
              <button type="button" className="btn btn-primary btn-sm" onClick={applyExtractedFields}>
                Use extracted fields
              </button>
            </div>
            <div className="grid-2">
              <div>
                <h3>Extracted fields</h3>
                <dl className="details compact">
                  {Object.entries(upload.extracted_fields).map(([key, value]) => (
                    <div key={key}>
                      <dt>{key.replaceAll("_", " ")}</dt>
                      <dd>{value || <span className="muted">not found</span>}</dd>
                    </div>
                  ))}
                </dl>
              </div>
              <div>
                <h3>Extracted text</h3>
                <pre className="text-preview">{upload.text_preview}</pre>
              </div>
            </div>
            <p className="muted small">The document will be linked to the case when you create it.</p>
          </div>
        )}
      </section>

      <section className="card">
        <h2>{upload ? "Review and complete the case" : "Option B — Enter the case manually"}</h2>
        <form onSubmit={handleSubmit} noValidate>
          <CaseForm form={form} setForm={setForm} errors={errors} />
          <Alert>{error}</Alert>
          <div className="form-actions">
            <button type="button" className="btn btn-ghost" onClick={() => navigate("/cases")}>
              Cancel
            </button>
            <button className="btn btn-primary" disabled={saving}>
              {saving ? "Creating…" : "Create case"}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
