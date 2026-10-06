# RxResolveAI — Project Audit Report

**Date of Audit:** October 6, 2026  
**Auditor:** Antigravity AI Assistant  
**Repository:** `RxResolve-AI`

---

## 1. Project Overview

**RxResolveAI** is an AI-assisted decision support and administrative workflow system designed for pharmacy and healthcare administrative staff. It streamlines the resolution of prescription and insurance claim rejections by analyzing rejection messages/codes, retrieving relevant policy excerpts from a local knowledge base, generating plain-language explanations and next steps, and assisting with prior authorization (PA) documentation.

### Core Objectives
* **Demystify Rejections:** Translate opaque rejection codes and phrases (e.g., `PA001`, `70`, `M/I Prescriber ID`) into plain-language explanations.
* **Grounding in Policies:** Match rejection contexts against local payer policy documents using TF-IDF policy search.
* **PA Workflow Assistance:** Automatically generate tailored prior authorization checklists and editable draft request letters.
* **Human-in-the-Loop Governance:** Ensure all AI outputs are explicitly labeled as drafts requiring authorized human review before any administrative action is taken.

---

## 2. Existing Tech Stack

| Layer | Technology / Library | Version / Details |
|-------|----------------------|-------------------|
| **Frontend Framework** | React | `^18.3.1` |
| **Build Tool** | Vite | `^5.4.11` |
| **Routing** | React Router DOM | `^6.28.0` |
| **Styling** | Vanilla CSS (CSS Variables) | Custom responsive stylesheet (`styles.css`) |
| **Backend Framework** | Python / FastAPI | `fastAPI >= 0.110` with `uvicorn` |
| **ORM / Database** | SQLAlchemy 2.0 & SQLite | `rxresolve.db` (single-file local database) |
| **Validation & Serialization** | Pydantic v2 | `pydantic >= 2.6` |
| **Document Processing** | PyPDF & python-docx | PDF and DOCX text extraction |
| **Information Retrieval** | Plain Python TF-IDF + Cosine Similarity | Custom term-frequency/inverse-document-frequency search over `sample_policies/` |
| **AI / LLM Integration** | Local Ollama (Optional) with Rule-Based Fallback | Default model `llama3.2`; fallback to rule-based templates if Ollama is unavailable |
| **Authentication** | Custom Local Auth | PBKDF2-SHA256 password hashing (200,000 iterations), 256-bit bearer session tokens |
| **Testing** | pytest + FastAPI TestClient | 50 backend automated unit and integration tests |

---

## 3. Existing Architecture & Workflows

### Architecture Blueprint

```text
               Browser (React 18 + Vite 5, http://localhost:5173)
                                 │
                          /api/* (Vite Proxy)
                                 ▼
                     FastAPI Backend (http://localhost:8000)
                                 │
     ┌──────────────────┬────────┴──────────┬───────────────────┬──────────────────┐
     ▼                  ▼                   ▼                   ▼                  ▼
document_processor  classifier        policy_search        ai_service         pa_assistant
(pypdf, python-docx)(Rule engine:     (TF-IDF + Cosine     (Ollama LLM or     (Checklist &
 multi-keyword &     codes/keywords)   similarity over      Rule-based         editable draft)
 extraction)                           sample_policies/)    template)
                                 │
                                 ▼
                       SQLite (rxresolve.db)
```

### Key Application Workflows

1. **Rejection Capture & Extraction:** Staff creates a case manually or uploads a PDF/DOCX/TXT notice. `document_processor.py` extracts text and pre-fills form fields (medication, payer, code, message).
2. **AI Classification & Analysis:** `POST /api/cases/{id}/analyze` runs `classifier.py` and `policy_search.py`. If Ollama is available, `ai_service.py` synthesizes policy excerpts into a plain-language summary; otherwise, rule-based templates provide deterministic guidance.
3. **Prior Authorization Assistance:** `pa_assistant.py` checks case criteria to build a status-aware checklist and pre-populates an editable PA request letter.
4. **Status & History Tracking:** Status changes (`New` → `Under Review` → `PA Required` → `Waiting for Information` → `Submitted` → `Resolved`) record audit logs in `case_status_history`.

---

## 4. Existing Database Schema

* **`users`**: `id`, `username`, `hashed_password`, `full_name`, `role`, `created_at`
* **`sessions`**: `id`, `token`, `user_id`, `created_at`, `expires_at`
* **`cases`**: `id`, `patient_id`, `claim_id`, `medication`, `payer`, `rejection_code`, `rejection_message`, `quantity`, `date_of_service`, `prescriber_id`, `additional_notes`, `status`, `rejection_category`, `confidence_level`, `classification_reason`, `explanation`, `suggested_next_step`, `missing_information`, `policy_excerpts`, `pa_checklist`, `pa_draft`, `created_at`, `updated_at`
* **`documents`**: `id`, `filename`, `file_type`, `extracted_text`, `uploaded_at`
* **`case_documents`**: `id`, `case_id`, `document_id`, `linked_at`
* **`case_status_history`**: `id`, `case_id`, `previous_status`, `new_status`, `note`, `changed_at`

---

## 5. Existing API Endpoints Inventory

| Method | Endpoint Path | Description | Auth Required |
|--------|---------------|-------------|---------------|
| `POST` | `/api/login` | Authenticates user and issues bearer token | No |
| `POST` | `/api/logout` | Revokes current session token | Yes |
| `GET` | `/api/me` | Returns details of currently authenticated user | Yes |
| `GET` | `/api/dashboard` | Aggregates case counts, status breakdown, category metrics | Yes |
| `GET` | `/api/ai/status` | Checks Ollama connection status and active model | Yes |
| `GET` | `/api/cases` | Lists cases with optional query/status/category filters | Yes |
| `POST` | `/api/cases` | Creates a new rejection resolution case | Yes |
| `GET` | `/api/cases/{id}` | Retrieves full case detail including history & policy matches | Yes |
| `PUT` | `/api/cases/{id}` | Modifies existing case details | Yes |
| `DELETE` | `/api/cases/{id}` | Deletes a case and related linkage | Yes |
| `PUT` | `/api/cases/{id}/status` | Updates case status and appends to audit log | Yes |
| `POST` | `/api/cases/{id}/analyze` | Triggers classification, policy search, and AI explanation | Yes |
| `POST` | `/api/cases/{id}/pa-draft` | Generates PA checklist and initial letter draft | Yes |
| `PUT` | `/api/cases/{id}/pa-draft` | Saves user edits to the PA letter draft | Yes |
| `PUT` | `/api/cases/{id}/pa-checklist` | Updates checklist item states | Yes |
| `POST` | `/api/upload` | Uploads PDF/DOCX/TXT file & extracts text/fields | Yes |
| `GET` | `/api/documents/{id}` | Fetches extracted text for an uploaded file | Yes |
| `GET` | `/api/policies` | Lists available sample policy documents | Yes |
| `GET` | `/api/policies/search` | Performs TF-IDF policy search | Yes |
| `GET` | `/api/policies/{filename}` | Reads full text of a sample policy document | Yes |
| `POST` | `/api/policies/upload` | Uploads a new text policy document to `sample_policies/` | Yes |
| `GET` | `/api/health` | Health check endpoint returning API status & disclaimer | No |

---

## 6. Existing Feature Inventory

| Feature | Exists? | Working? | Files / Location | Notes |
|---------|---------|----------|------------------|-------|
| User Authentication | Yes | Yes | `backend/auth.py`, `backend/routers/auth_routes.py`, `frontend/src/pages/LoginPage.jsx` | PBKDF2 hashed demo accounts (`admin`, `staff`). |
| Dashboard Statistics | Yes | Yes | `backend/routers/dashboard.py`, `frontend/src/pages/DashboardPage.jsx` | Displays stat cards, category bars, status metrics, and recent cases. |
| Case Creation | Yes | Yes | `backend/routers/cases.py`, `frontend/src/pages/CreateCasePage.jsx` | Supports manual entry, pre-fill demo data, or document extraction. |
| File Upload & Extraction | Yes | Yes | `backend/document_processor.py`, `backend/routers/documents.py` | Parses `.pdf`, `.docx`, and `.txt` files; extracts key fields. |
| Rejection Classification | Yes | Yes | `backend/classifier.py` | 8 distinct rejection categories with confidence scoring. |
| AI Plain Language Analysis | Yes | Yes | `backend/ai_service.py` | Uses Ollama local LLM if available; falls back smoothly to rules. |
| Policy Knowledge Base Search | Yes | Yes | `backend/policy_search.py`, `backend/routers/policies.py` | TF-IDF & cosine similarity search over `sample_policies/`. |
| Prior Authorization Assistant | Yes | Yes | `backend/pa_assistant.py`, `frontend/src/pages/PriorAuthPage.jsx` | Generates PA checklists and editable draft letters. |
| Case Audit & History Tracking | Yes | Yes | `backend/models.py`, `frontend/src/components/StatusChanger.jsx` | Full timeline history log of status transitions. |
| Case Search & Filter | Yes | Yes | `backend/routers/cases.py`, `frontend/src/pages/CasesPage.jsx` | Search across patient ID, claim ID, drug, payer; filter by category/status. |
| Automated Test Suite | Yes | Yes | `backend/tests/` | 50 passing pytest test cases covering backend APIs and edge cases. |

---

## 7. Audit Conclusion & Identified UI/UX Opportunities

The backend, database schema, AI pipelines, policy search, document extraction, and business logic are robust, complete, and verified by test suites. 

### Key UI/UX Improvement Opportunities
1. **Visual Theme:** Replace the legacy heavy-green color palette (`--primary: #0f766e`) with a modern, calm, relaxing healthcare-slate theme.
2. **Light / Dark Mode:** Implement a high-contrast Light and Dark mode toggle with seamless transitions and local storage persistence.
3. **Landing Page:** Create an engaging, modern animated landing page to introduce RxResolveAI before authentication, showcasing how the system works without making medical claims.
4. **App Workspace Aesthetics:** Enhance the Dashboard, Case Details, Policy Search, and PA Assistant components with clean typography, polished status badges, subtle hover micro-interactions, responsive sidebars, skeleton loaders, and empty states.
