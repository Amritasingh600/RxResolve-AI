import { useEffect, useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout.jsx";
import { getStoredUser, getToken } from "./services/api.js";
import LandingPage from "./pages/LandingPage.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import DashboardPage from "./pages/DashboardPage.jsx";
import CasesPage from "./pages/CasesPage.jsx";
import CreateCasePage from "./pages/CreateCasePage.jsx";
import CaseDetailsPage from "./pages/CaseDetailsPage.jsx";
import PolicyDocumentsPage from "./pages/PolicyDocumentsPage.jsx";
import PriorAuthPage from "./pages/PriorAuthPage.jsx";
import { getInitialTheme, applyTheme } from "./utils/theme.js";

export default function App() {
  const [user, setUser] = useState(() => (getToken() ? getStoredUser() : null));

  useEffect(() => {
    // Initialize theme on app boot
    applyTheme(getInitialTheme());
  }, []);

  if (!user) {
    return (
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/landing" element={<LandingPage />} />
        <Route path="/login" element={<LoginPage onLogin={setUser} />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    );
  }

  return (
    <Layout user={user} onLogout={() => setUser(null)}>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/landing" element={<LandingPage />} />
        <Route path="/cases" element={<CasesPage />} />
        <Route path="/cases/new" element={<CreateCasePage />} />
        <Route path="/cases/:id" element={<CaseDetailsPage />} />
        <Route path="/policies" element={<PolicyDocumentsPage />} />
        <Route path="/pa" element={<PriorAuthPage />} />
        <Route path="/pa/:id" element={<PriorAuthPage />} />
        <Route path="/login" element={<Navigate to="/" replace />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  );
}
