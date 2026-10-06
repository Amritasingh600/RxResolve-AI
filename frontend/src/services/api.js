// All communication with the FastAPI backend goes through this file.
// The login token is kept in localStorage and sent as "Authorization: Bearer <token>".

const TOKEN_KEY = "rxresolve_token";
const USER_KEY = "rxresolve_user";

export function getToken() {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function getStoredUser() {
  try {
    return JSON.parse(localStorage.getItem(USER_KEY) || "null");
  } catch {
    return null;
  }
}

function saveSession(token, user) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

// Turn FastAPI error bodies into a readable message.
function errorMessage(body, status) {
  if (!body || !body.detail) return `Request failed (HTTP ${status}).`;
  if (typeof body.detail === "string") return body.detail;
  if (Array.isArray(body.detail)) {
    // Pydantic validation errors: [{loc: ["body", "medication"], msg: "..."}]
    return body.detail
      .map((err) => {
        const field = (err.loc || []).filter((part) => part !== "body").join(".");
        return field ? `${field.replaceAll("_", " ")}: ${err.msg}` : err.msg;
      })
      .join("; ");
  }
  return `Request failed (HTTP ${status}).`;
}

async function request(path, { method = "GET", body, formData } = {}) {
  const headers = {};
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body !== undefined) headers["Content-Type"] = "application/json";

  let response;
  try {
    response = await fetch(path, {
      method,
      headers,
      body: formData ?? (body !== undefined ? JSON.stringify(body) : undefined),
    });
  } catch {
    throw new Error("Cannot reach the RxResolveAI server. Is the backend running on port 8000?");
  }

  if (response.status === 401 && path !== "/api/login") {
    clearSession();
    window.location.href = "/login";
    throw new Error("Your session has expired. Please log in again.");
  }
  if (response.status === 204) return null;

  const data = await response.json().catch(() => null);
  if (!response.ok) throw new Error(errorMessage(data, response.status));
  return data;
}

function uploadForm(file, extra = {}) {
  const formData = new FormData();
  formData.append("file", file);
  Object.entries(extra).forEach(([key, value]) => {
    if (value !== undefined && value !== null) formData.append(key, value);
  });
  return formData;
}

export const api = {
  async login(username, password) {
    const data = await request("/api/login", { method: "POST", body: { username, password } });
    saveSession(data.token, data.user);
    return data.user;
  },
  async logout() {
    try {
      await request("/api/logout", { method: "POST" });
    } finally {
      clearSession();
    }
  },

  getDashboard: () => request("/api/dashboard"),
  getAiStatus: () => request("/api/ai/status"),

  getCases(filters = {}) {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => value && params.append(key, value));
    const query = params.toString();
    return request(`/api/cases${query ? `?${query}` : ""}`);
  },
  getCase: (id) => request(`/api/cases/${id}`),
  createCase: (data) => request("/api/cases", { method: "POST", body: data }),
  updateCase: (id, data) => request(`/api/cases/${id}`, { method: "PUT", body: data }),
  deleteCase: (id) => request(`/api/cases/${id}`, { method: "DELETE" }),
  updateStatus: (id, status, note) => request(`/api/cases/${id}/status`, { method: "PUT", body: { status, note } }),
  analyzeCase: (id) => request(`/api/cases/${id}/analyze`, { method: "POST" }),

  generatePaDraft: (id) => request(`/api/cases/${id}/pa-draft`, { method: "POST" }),
  savePaDraft: (id, text) => request(`/api/cases/${id}/pa-draft`, { method: "PUT", body: { pa_draft: text } }),
  updateChecklist: (id, items) => request(`/api/cases/${id}/pa-checklist`, { method: "PUT", body: { items } }),

  uploadDocument: (file, caseId) => request("/api/upload", { method: "POST", formData: uploadForm(file, { case_id: caseId }) }),
  getDocument: (id) => request(`/api/documents/${id}`),

  getPolicies: () => request("/api/policies"),
  getPolicy: (filename) => request(`/api/policies/${encodeURIComponent(filename)}`),
  searchPolicies: (q) => request(`/api/policies/search?q=${encodeURIComponent(q)}`),
  uploadPolicy: (file) => request("/api/policies/upload", { method: "POST", formData: uploadForm(file) }),
};

export const CASE_STATUSES = ["New", "Under Review", "PA Required", "Waiting for Information", "Submitted", "Resolved"];

export const CATEGORIES = [
  "Prior Authorization Required",
  "Drug Not Covered",
  "Quantity Limit",
  "Refill Too Soon",
  "Step Therapy",
  "Eligibility Problem",
  "Missing Information",
  "Other",
];
