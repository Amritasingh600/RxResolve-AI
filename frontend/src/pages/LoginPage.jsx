import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import Disclaimer from "../components/Disclaimer.jsx";
import { Alert } from "../components/Feedback.jsx";
import ThemeToggle from "../components/ThemeToggle.jsx";
import { api } from "../services/api.js";

export default function LoginPage({ onLogin }) {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    if (!username.trim() || !password) {
      setError("Please enter your username and password.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const user = await api.login(username.trim(), password);
      onLogin(user);
      navigate("/");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function fillDemo(u, p) {
    setUsername(u);
    setPassword(p);
    setError("");
  }

  return (
    <div className="login-page">
      <div className="login-top-bar">
        <Link to="/" className="btn btn-ghost btn-sm">
          ← Back to Overview
        </Link>
        <ThemeToggle />
      </div>

      <div className="login-card card">
        <div className="brand login-brand">
          <span className="brand-mark">Rx</span>
          <div>
            <div className="brand-name">RxResolveAI</div>
            <div className="brand-sub">Claim rejection &amp; prior authorization assistant</div>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="form">
          <label className="field">
            <span>Username</span>
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="e.g. admin or staff"
              autoComplete="username"
              autoFocus
            />
          </label>
          <label className="field">
            <span>Password</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              autoComplete="current-password"
            />
          </label>
          <Alert>{error}</Alert>
          <button className="btn btn-primary btn-block" disabled={loading}>
            {loading ? "Signing in…" : "Sign in to Workspace ➔"}
          </button>
        </form>

        <div className="demo-credentials">
          <div className="demo-title">Quick Demo Login:</div>
          <div className="demo-buttons">
            <button
              type="button"
              className="btn btn-ghost btn-sm demo-btn"
              onClick={() => fillDemo("admin", "admin123")}
            >
              🔑 Admin Demo
            </button>
            <button
              type="button"
              className="btn btn-ghost btn-sm demo-btn"
              onClick={() => fillDemo("staff", "staff123")}
            >
              📋 Staff Demo
            </button>
          </div>
        </div>

        <Disclaimer compact />
      </div>
    </div>
  );
}
