import { Link } from "react-router-dom";

export default function StatCard({ label, value, hint, accent = "teal", to }) {
  const content = (
    <>
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
      {hint && <div className="stat-hint">{hint}</div>}
    </>
  );
  return to ? (
    <Link to={to} className={`card stat-card accent-${accent}`}>
      {content}
    </Link>
  ) : (
    <div className={`card stat-card accent-${accent}`}>{content}</div>
  );
}
