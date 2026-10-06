import { useEffect, useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { api } from "../services/api.js";
import Disclaimer from "./Disclaimer.jsx";
import ThemeToggle from "./ThemeToggle.jsx";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", icon: "▦", end: true },
  { to: "/cases", label: "Cases", icon: "☰", end: true },
  { to: "/cases/new", label: "Create Case", icon: "+" },
  { to: "/pa", label: "Prior Authorization", icon: "✓" },
  { to: "/policies", label: "Policy Documents", icon: "▤" },
  { to: "/landing", label: "Overview", icon: "ⓘ" },
];

export default function Layout({ user, onLogout, children }) {
  const navigate = useNavigate();
  const [aiStatus, setAiStatus] = useState(null);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    api.getAiStatus().then(setAiStatus).catch(() => setAiStatus(null));
  }, []);

  async function handleLogout() {
    await api.logout().catch(() => {});
    onLogout();
    navigate("/landing");
  }

  return (
    <div className="app-shell">
      <aside className={`sidebar ${menuOpen ? "open" : ""}`}>
        <div className="brand">
          <span className="brand-mark">Rx</span>
          <div>
            <div className="brand-name">RxResolveAI</div>
            <div className="brand-sub">Rejection support · demo</div>
          </div>
          <button className="menu-toggle" onClick={() => setMenuOpen(!menuOpen)} aria-label="Toggle menu">
            ☰
          </button>
        </div>

        <nav className="nav" onClick={() => setMenuOpen(false)}>
          {NAV_ITEMS.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.end} className="nav-link">
              <span className="nav-icon" aria-hidden="true">{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="sidebar-controls">
            <ThemeToggle className="sidebar-theme-toggle" />
          </div>

          {aiStatus && (
            <div className={`ai-pill ${aiStatus.available ? "on" : "off"}`} title={aiStatus.detail}>
              <span className="dot" />
              {aiStatus.available ? `Local AI: ${aiStatus.model}` : "Rule-based mode"}
            </div>
          )}

          <div className="user-box">
            <div className="user-info">
              <div className="user-avatar">{user.username.charAt(0).toUpperCase()}</div>
              <div>
                <div className="user-name">{user.full_name || user.username}</div>
                <div className="muted small">@{user.username}</div>
              </div>
            </div>
            <button className="btn btn-ghost btn-sm logout-btn" onClick={handleLogout} title="Log out">
              Log out
            </button>
          </div>
        </div>
      </aside>

      <main className="main">
        <Disclaimer />
        {children}
      </main>
    </div>
  );
}
