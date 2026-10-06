import { Link, useNavigate } from "react-router-dom";
import { formatDate } from "../utils/format.js";
import { CategoryBadge, ConfidenceBadge, StatusBadge } from "./Badges.jsx";

// Table of cases used by the Dashboard, Cases and PA pages.
export default function CaseTable({ cases, linkPrefix = "/cases", compact = false }) {
  const navigate = useNavigate();

  return (
    <div className="table-wrap">
      <table className="table">
        <thead>
          <tr>
            <th>Case</th>
            <th>Patient ID</th>
            <th>Medication</th>
            {!compact && <th>Insurance</th>}
            <th>Category</th>
            {!compact && <th>Confidence</th>}
            <th>Status</th>
            <th>Created</th>
          </tr>
        </thead>
        <tbody>
          {cases.map((c) => (
            <tr key={c.id} className="clickable" onClick={() => navigate(`${linkPrefix}/${c.id}`)}>
              <td>
                <Link to={`${linkPrefix}/${c.id}`} onClick={(e) => e.stopPropagation()}>
                  #{c.id}
                </Link>
                <div className="muted small">{c.claim_id}</div>
              </td>
              <td>{c.patient_id}</td>
              <td>{c.medication}</td>
              {!compact && <td>{c.insurance}</td>}
              <td>
                <CategoryBadge category={c.category} />
              </td>
              {!compact && (
                <td>
                  <ConfidenceBadge confidence={c.confidence} />
                </td>
              )}
              <td>
                <StatusBadge status={c.status} />
              </td>
              <td className="nowrap">{formatDate(c.created_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
