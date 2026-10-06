import { useState } from "react";
import { api, CASE_STATUSES } from "../services/api.js";
import { StatusBadge } from "./Badges.jsx";

// Lets staff change the workflow status of a case (stored with history in SQLite).
export default function StatusChanger({ caseData, onUpdated, onError }) {
  const [status, setStatus] = useState(caseData.status);
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);

  async function handleSave(event) {
    event.preventDefault();
    setSaving(true);
    try {
      const updated = await api.updateStatus(caseData.id, status, note || null);
      setNote("");
      onUpdated(updated);
    } catch (error) {
      onError(error.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="status-changer" onSubmit={handleSave}>
      <div className="muted small">
        Current status: <StatusBadge status={caseData.status} />
      </div>
      <div className="status-row">
        <select value={status} onChange={(e) => setStatus(e.target.value)} aria-label="New status">
          {CASE_STATUSES.map((s) => (
            <option key={s}>{s}</option>
          ))}
        </select>
        <input
          type="text"
          placeholder="Optional note (e.g. who approved)"
          maxLength={500}
          value={note}
          onChange={(e) => setNote(e.target.value)}
        />
        <button className="btn btn-primary" disabled={saving || status === caseData.status}>
          {saving ? "Saving…" : "Update status"}
        </button>
      </div>
    </form>
  );
}
