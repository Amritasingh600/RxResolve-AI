import { useEffect, useState } from "react";
import { applyTheme, getInitialTheme } from "../utils/theme.js";

export default function ThemeToggle({ className = "" }) {
  const [theme, setTheme] = useState(getInitialTheme);

  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  function toggleTheme() {
    const nextTheme = theme === "light" ? "dark" : "light";
    setTheme(nextTheme);
  }

  return (
    <button
      type="button"
      className={`theme-toggle-btn ${className}`}
      onClick={toggleTheme}
      title={`Switch to ${theme === "light" ? "dark" : "light"} mode`}
      aria-label={`Switch to ${theme === "light" ? "dark" : "light"} mode`}
    >
      {theme === "light" ? (
        <>
          <span className="theme-toggle-icon">🌙</span>
          <span className="theme-toggle-text">Dark</span>
        </>
      ) : (
        <>
          <span className="theme-toggle-icon">☀</span>
          <span className="theme-toggle-text">Light</span>
        </>
      )}
    </button>
  );
}
