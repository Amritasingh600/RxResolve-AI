import { confidenceLabel } from "../utils/format.js";

const STATUS_CLASS = {
  New: "badge-blue",
  "Under Review": "badge-purple",
  "PA Required": "badge-orange",
  "Waiting for Information": "badge-yellow",
  Submitted: "badge-teal",
  Resolved: "badge-green",
};

export function StatusBadge({ status }) {
  return <span className={`badge ${STATUS_CLASS[status] || "badge-gray"}`}>{status}</span>;
}

export function CategoryBadge({ category }) {
  if (!category) return <span className="badge badge-gray">Not analyzed</span>;
  const className = category === "Other" ? "badge-gray" : "badge-outline";
  return <span className={`badge ${className}`}>{category}</span>;
}

export function ConfidenceBadge({ confidence, showPercent = true }) {
  const label = confidenceLabel(confidence);
  if (!label) return <span className="muted">—</span>;
  return (
    <span className={`confidence confidence-${label.toLowerCase()}`}>
      {label}
      {showPercent && ` · ${Math.round(confidence * 100)}%`}
    </span>
  );
}
