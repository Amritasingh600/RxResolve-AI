import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import CaseTable from "../components/CaseTable.jsx";
import { Alert, EmptyState, Loading } from "../components/Feedback.jsx";
import StatCard from "../components/StatCard.jsx";
import { api } from "../services/api.js";

export default function DashboardPage() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.getDashboard().then(setData).catch((err) => setError(err.message));
  }, []);

  if (error) return <Alert>{error}</Alert>;
  if (!data) return <Loading />;

  const maxCategoryCount = Math.max(1, ...Object.values(data.by_category));

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Dashboard</h1>
          <p className="muted">Overview of prescription / claim rejection cases.</p>
        </div>
        <Link to="/cases/new" className="btn btn-primary">
          + New case
        </Link>
      </div>

      <div className="stat-grid">
        <StatCard label="Total cases" value={data.total_cases} accent="teal" to="/cases" />
        <StatCard label="Pending cases" value={data.pending_cases} hint="Not yet resolved" accent="blue" to="/cases" />
        <StatCard label="Resolved cases" value={data.resolved_cases} accent="green" to="/cases?status=Resolved" />
        <StatCard label="Prior authorization" value={data.pa_cases} hint="Category or status PA" accent="orange" to="/pa" />
      </div>

      <div className="grid-2">
        <section className="card">
          <h2>Cases by status</h2>
          <ul className="count-list">
            {Object.entries(data.by_status).map(([status, count]) => (
              <li key={status}>
                <Link to={`/cases?status=${encodeURIComponent(status)}`}>{status}</Link>
                <span className="count">{count}</span>
              </li>
            ))}
          </ul>
        </section>
        <section className="card">
          <h2>Cases by rejection category</h2>
          {Object.keys(data.by_category).length === 0 ? (
            <p className="muted">No cases yet.</p>
          ) : (
            <ul className="bar-list">
              {Object.entries(data.by_category)
                .sort((a, b) => b[1] - a[1])
                .map(([category, count]) => (
                  <li key={category}>
                    <div className="bar-label">
                      <span>{category}</span>
                      <span className="count">{count}</span>
                    </div>
                    <div className="bar-track">
                      <div className="bar-fill" style={{ width: `${(count / maxCategoryCount) * 100}%` }} />
                    </div>
                  </li>
                ))}
            </ul>
          )}
        </section>
      </div>

      <section className="card">
        <div className="card-header">
          <h2>Recent cases</h2>
          <Link to="/cases">View all →</Link>
        </div>
        {data.recent_cases.length === 0 ? (
          <EmptyState title="No cases yet">
            <Link to="/cases/new">Create the first case</Link>
          </EmptyState>
        ) : (
          <CaseTable cases={data.recent_cases} compact />
        )}
      </section>
    </div>
  );
}
