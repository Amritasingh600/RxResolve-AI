# RxResolveAI

**AI-assisted administrative decision support for prescription claim rejections and prior authorization (PA).**

> RxResolveAI provides AI-assisted administrative guidance. All recommendations and generated documents must be
> reviewed by authorized staff before use.

RxResolveAI is a student project (React + FastAPI + SQLite). It runs completely on your own computer and uses only
free tools. A local LLM (Ollama) is **optional**: without it, the app uses a rule-based classifier and templates.

---

## 1. Project overview

Pharmacy and clinic staff often receive claim rejections with short, confusing messages such as
*"Prior authorization required"*, *"Plan limitations exceeded"* or *"M/I Prescriber ID"*. RxResolveAI helps staff:

1. record the rejection (typed in, or extracted from an uploaded PDF / DOCX / TXT),
2. classify the rejection into a category, with a confidence level,
3. find the relevant text in a local (sample) policy knowledge base,
4. explain in plain language what happened and what to do next,
5. prepare a PA checklist and a **draft** request, which staff review,
6. track the case status until it is resolved.

## 2. Problem statement

Understanding a rejection, checking the policy, collecting documents and deciding the next step is manual, repetitive
work. It causes delays, confusion and administrative burden, and can delay a patient's access to medication.

## 3. Proposed solution

A small web application that organizes this work and gives consistent guidance:

- **Rule-based classification** (rejection code + keywords) that always works and is easy to explain.
- **TF-IDF policy search** over local text files, which grounds the explanation in documents.
- **Optional local LLM** (Ollama) that only rewrites explanations and draft paragraphs. It never decides the
  category when the rules already found one, and it never invents payer rules.
- **Human-in-the-loop**: every result is labelled "Pending human review". Drafts are labelled
  "AI-generated draft — requires human review". Nothing is ever sent to an insurer.

**What RxResolveAI does NOT do:** it does not diagnose, prescribe, make clinical decisions, approve or deny
treatment, submit claims or PA requests, or connect to any real payer, pharmacy or patient-record system.

## 4. Features

| # | Feature | Where |
|---|---------|-------|
| 1 | Dashboard: total / pending / resolved / PA cases, cases by status and by category, recent cases | Dashboard |
| 2 | Create a case (patient ID, claim ID, medication, payer, code, message, quantity, date, prescriber, notes) | Create Case |
| 3 | Upload a PDF / DOCX / TXT rejection notice → extract the text → pre-fill the form | Create Case, Case Details |
| 4 | Rejection classification (8 categories) with confidence, reason and suggested next step | Case Details |
| 5 | Local policy knowledge base with TF-IDF search; add new sample policies | Policy Documents |
| 6 | Plain-language explanation: what happened, possible reason, what staff should do, missing info | Case Details |
| 7 | PA assistant: automatic and manual checklist items, draft request (editable, copy, download .txt) | Prior Authorization |
| 8 | Status tracking (New → Under Review → PA Required → Waiting for Information → Submitted → Resolved), with a history log | Case Details, PA |
| 9 | Search (patient ID, case #, claim ID, medication, payer, category) and filters (status, category) | Cases |
| 10 | Case details page with all sections (information, rejection, analysis, policy, PA, documents, status) | Case Details |
| 11 | Modern animated landing page introducing RxResolveAI value proposition, workflow, and governance | Landing Page (`/landing`) |
| 12 | Dual Light and Dark mode theme switcher with local storage persistence | Navigation Sidebar / Topbar |
| 13 | Calm, relaxing healthcare-slate visual design system with micro-animations | Workspace & Landing Page |

## 5. Architecture

```
            Browser (React + Vite, http://localhost:5173)
                               │  /api/* (Vite proxy)
                               ▼
                   FastAPI backend (http://localhost:8000)
                               │
  ┌───────────────┬────────────┼──────────────────┬──────────────────┐
  ▼               ▼            ▼                  ▼                  ▼
document_      classifier   policy_search       ai_service        pa_assistant
processor      (rules:      (TF-IDF +           (pipeline +       (checklist +
(pypdf,        codes +      cosine over         optional          draft request)
python-docx)   keywords)    sample_policies/)   Ollama)
                               │
                               ▼
                         SQLite (rxresolve.db)
```

**Analysis pipeline** (`POST /api/cases/{id}/analyze`):

```
User input → Information extraction → Rejection classification (rules)
           → Policy search (TF-IDF) → Explanation (template, or local LLM if available)
           → Suggested next step + missing information → Human review
```

**AI fallback logic** (`backend/ai_service.py`):

```
if Ollama is running and the model is installed:
    rules classify → LLM rewrites the explanation using ONLY the case + policy excerpts
    (if the rules find nothing, the LLM may suggest one of the known categories,
     which is capped at 50% confidence and labelled "verify manually")
else:
    rules classify → template explanation
```

## 6. Tech stack

| Layer | Technology (all free) |
|-------|-----------------------|
| Frontend | React 18, Vite 5, React Router, plain CSS |
| Backend | Python 3.10+, FastAPI, Pydantic v2, SQLAlchemy 2 |
| Database | SQLite (one file, created automatically) |
| Documents | pypdf, python-docx |
| Search | TF-IDF + cosine similarity in plain Python (no vector database) |
| AI (optional) | Ollama with a local open-source model (default `llama3.2`) |
| Auth | Local users, PBKDF2-SHA256 password hashing, random session tokens |
| Tests | pytest + FastAPI TestClient |

## 7. Folder structure

```
RxResolve-AI/
├── backend/
│   ├── main.py               # FastAPI app, startup (create tables + demo data), error handler
│   ├── config.py             # settings (can be overridden with environment variables)
│   ├── database.py           # SQLite engine / session
│   ├── models.py             # tables: users, sessions, cases, documents, case_documents, case_status_history
│   ├── schemas.py            # Pydantic request/response models + validation
│   ├── auth.py               # password hashing, login sessions
│   ├── classifier.py         # rule-based rejection classifier + plain-language guidance
│   ├── policy_search.py      # TF-IDF policy search
│   ├── ai_service.py         # analysis pipeline + optional Ollama
│   ├── pa_assistant.py       # PA checklist + draft generation
│   ├── document_processor.py # upload validation, text + field extraction
│   ├── seed.py               # demo users + sample cases
│   ├── routers/              # API endpoints (auth, cases, documents, policies, dashboard)
│   ├── tests/                # pytest tests
│   ├── pytest.ini
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/       # Layout, badges, forms, tables, analysis panel, …
│   │   ├── pages/            # Login, Dashboard, Cases, CreateCase, CaseDetails, PolicyDocuments, PriorAuth
│   │   ├── services/api.js   # all backend calls
│   │   ├── utils/format.js
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── styles.css
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── sample_policies/          # 7 fictional policy documents (knowledge base)
├── sample_data/              # 10 fictional sample cases + sample rejection notices (TXT, PDF, DOCX)
├── README.md
└── .gitignore
```

## 8. Installation

Requirements:

- **Python 3.10 or newer**: https://www.python.org/downloads/
- **Node.js 18 or newer** (includes npm): https://nodejs.org/
- *(optional)* **Ollama**: https://ollama.com/download

Get the project folder onto your computer (clone it or unzip it), then open **two terminals** in the project root:
one for the backend and one for the frontend.

## 9. Running the backend

```bash
cd backend
python -m venv venv
```

Activate the virtual environment. On **Windows**:

```bash
venv\Scripts\activate
```

On **macOS / Linux**:

```bash
source venv/bin/activate
```

Install the dependencies and start the server:

```bash
pip install -r requirements.txt
```

```bash
uvicorn main:app --reload
```

The API runs at http://localhost:8000. Interactive API docs are at http://localhost:8000/docs.
On first start, the database `backend/rxresolve.db` is created with the demo users and 10 sample cases.

> To reset the demo data: stop the server, delete `backend/rxresolve.db`, and start it again.

## 10. Running the frontend

In the second terminal:

```bash
cd frontend
npm install
```

```bash
npm run dev
```

Open **http://localhost:5173** in your browser. The Vite dev server forwards `/api` requests to the backend on port 8000,
so the backend must be running too.

## 11. Installing Ollama (optional)

1. Download and install Ollama from https://ollama.com/download (free).
2. Download the default model (about 2 GB, one time only):

   ```bash
   ollama pull llama3.2
   ```

3. Make sure Ollama is running (the desktop app starts it automatically, or run `ollama serve`).
4. Restart the backend. The sidebar shows **"Local AI: llama3.2"** when the model is detected.

To use a different model, set an environment variable before starting the backend. For example, on Windows:

```bash
set OLLAMA_MODEL=qwen2.5:3b
```

On macOS / Linux:

```bash
export OLLAMA_MODEL=qwen2.5:3b
```

Small models (1B–3B parameters) run on a normal laptop CPU. Generating an explanation can take a few seconds to a
minute, depending on your hardware.

## 12. Running without Ollama

No setup is needed: if Ollama is not installed or not running, RxResolveAI automatically uses the rule-based classifier
and template text. The sidebar then shows **"Rule-based mode"**. Every feature works in this mode.

To force rule-based mode even when Ollama is installed, set `RXR_USE_OLLAMA=0` before starting the backend
(`set RXR_USE_OLLAMA=0` on Windows, `export RXR_USE_OLLAMA=0` on macOS / Linux).

## 13. Sample login credentials

| Username | Password | Role |
|----------|----------|------|
| `admin` | `admin123` | Demo administrator |
| `staff` | `staff123` | Demo pharmacy staff |

These are local demo accounts only. Change or remove them (in `backend/seed.py`) before using the app anywhere else.

## 14. Sample cases

All patients, payers (DemoHealth, MeadowCare Demo Plan, Summit Sample Health, RiverBend Demo Plan) and medications
(ExampleMed, Cardiozen, Painex ER, …) are **fictional**.

| # | Medication | Code | Rejection message | Category |
|---|------------|------|-------------------|----------|
| 1 | ExampleMed 50 mg | PA001 | Prior authorization required | Prior Authorization Required |
| 2 | Cardiozen 10 mg | 70 | Product/service not covered - non-formulary drug | Drug Not Covered |
| 3 | Painex ER 20 mg | 76 | Plan limitations exceeded - quantity limit of 60 tablets per 30 days | Quantity Limit |
| 4 | Allerfree 5 mg | 79 | Refill too soon - next fill date is 5 days from date of service | Refill Too Soon |
| 5 | Glucorin XR 500 mg | 608 | Step therapy required: trial of a preferred first-line agent must be on file | Step Therapy |
| 6 | Dermacort 0.1% cream | 65 | Patient not covered - coverage terminated | Eligibility Problem |
| 7 | Migrafen 25 mg | 25 | M/I Prescriber ID | Missing Information |
| 8 | Insulex pen | 75 | Prior authorization required. Missing clinical documentation. | Prior Authorization Required |
| 9 | Sleepwell 10 mg | — | Claim could not be processed. Contact help desk. | Other (manual review) |
| 10 | Asthmavent inhaler | QL001 | Quantity limit exceeded - maximum quantity 1 inhaler per 30 days | *(not analyzed yet, for the demo)* |

Sample documents for the upload feature are in `sample_data/`:
`sample_rejection_notice.txt`, `sample_rejection_notice.pdf` and `sample_rejection_notice.docx`.

### Demo flow

1. Log in as `admin` / `admin123`.
2. Look at the **Dashboard**.
3. Open **Create Case** and click **Fill demo example** (ExampleMed · DemoHealth · PA001 · "Prior authorization required"),
   or type the values yourself, or upload a file from `sample_data/` and click **Use extracted fields**.
4. Click **Create case**.
5. On the case page, click **Analyze Rejection**. The result is *Prior Authorization Required · High confidence*,
   with an explanation, next steps and the matching policy excerpt.
6. Click **Open PA Assistant**.
7. Click **Generate checklist & draft**.
8. Review and edit the draft, tick the checklist items you have confirmed, then **Save**.
9. Change the case status (for example to *Submitted*) and see it appear in the status history.

## 15. API endpoints

All endpoints except `/api/login` and `/api/health` require the header `Authorization: Bearer <token>`.

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/login` | Log in → `{token, user}` |
| POST | `/api/logout` | End the session |
| GET | `/api/me` | Current user |
| GET | `/api/dashboard` | Counts and recent cases |
| GET | `/api/ai/status` | Whether Ollama is available (or rule-based mode) |
| GET | `/api/cases?q=&status=&category=` | List / search / filter cases |
| POST | `/api/cases` | Create a case (optional `document_id` links an uploaded document) |
| GET | `/api/cases/{id}` | Case details (analysis, policy matches, PA data, documents, history) |
| PUT | `/api/cases/{id}` | Update case fields |
| DELETE | `/api/cases/{id}` | Delete a case |
| PUT | `/api/cases/{id}/status` | Change status `{status, note}` (recorded in the history) |
| POST | `/api/cases/{id}/analyze` | Classify + policy search + explanation |
| POST | `/api/cases/{id}/pa-draft` | Generate the PA checklist and draft |
| PUT | `/api/cases/{id}/pa-draft` | Save a draft edited by staff |
| PUT | `/api/cases/{id}/pa-checklist` | Save the manual checklist items |
| POST | `/api/cases/{id}/documents/{document_id}` | Link an uploaded document to a case |
| POST | `/api/upload` | Upload PDF/DOCX/TXT (multipart `file`, optional `case_id`) → text + extracted fields |
| GET | `/api/documents` / `/api/documents/{id}` | List documents / read extracted text |
| GET | `/api/policies` | List policy documents |
| GET | `/api/policies/search?q=` | Search the policy knowledge base |
| GET | `/api/policies/{filename}` | Read one policy document |
| POST | `/api/policies/upload` | Add a sample policy (saved as .txt in `sample_policies/`) |
| GET | `/api/health` | Health check |

## Running the tests

With the backend virtual environment activated:

```bash
cd backend
pytest
```

The tests use a temporary database and force rule-based mode, so they don't touch your demo data and don't need
Ollama. They cover rejection classification, policy search, case creation and retrieval, search/filter, the full
analyze → PA draft → status workflow, the AI fallback (Ollama disabled, unreachable, or failing), document uploads, and
invalid input (missing fields, wrong status, bad file types, oversized files, fake PDFs, path traversal).

## Security measures (student-project level)

- Passwords hashed with PBKDF2-SHA256 (200,000 iterations, random salt); random 256-bit session tokens that expire after 12 hours.
- Input validation with Pydantic (required fields, maximum lengths, allowed status values).
- Upload checks: allowed extensions (.pdf/.docx/.txt), 5 MB size limit, file signature check, sanitized file names.
  Only the extracted text is stored, not the original file.
- Policy file access is limited to plain file names inside `sample_policies/` (no path traversal).
- API errors return clear JSON messages; unexpected errors are logged and return a generic 500 message.

## Troubleshooting

| Problem | Cause and fix |
|---------|---------------|
| `The token '&&' is not a valid statement separator` | Windows PowerShell 5.1 does not support `&&`. Run each command on its own line, as shown above. |
| `cd frontend` fails: path not found | You are still inside `backend`. Use `cd ..\frontend` (Windows) or `cd ../frontend`. |
| http://localhost:8000 shows only a JSON message | This is expected: port 8000 is the API. The web app is at http://localhost:5173 (after `npm run dev`). API docs are at http://localhost:8000/docs. |
| Web app shows "Cannot reach the RxResolveAI server" | The backend is not running. Start it with `uvicorn main:app --reload` in the `backend` folder. |
| `venv\Scripts\activate` is blocked ("running scripts is disabled") | Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once in PowerShell, or use Command Prompt (cmd). |
| Port 8000 already in use | Another backend is still running. Stop it with Ctrl+C in its terminal, or start on another port with `uvicorn main:app --reload --port 8001` and change the proxy target in `frontend/vite.config.js`. |

## 16. Limitations

- Classification is keyword/code based. It can miss unusual wording (those cases go to "Other — manual review required").
- The knowledge base contains only fictional sample policies. Real payer policies differ and change often.
- Field extraction expects "Label: value" lines. Scanned PDFs (images) are not supported, because there is no OCR.
- Local LLM output quality depends on the model and can be wrong. That is why it only rewrites text, the rules keep
  the final say on the category, and everything is labelled for human review.
- There is no real payer integration. "Submitted" is only a status that staff set after acting outside the system.
- Simple authentication with no roles or permissions. It is not designed for real patient data (no HIPAA-level
  controls, audit logging or encryption at rest).

## 17. Future improvements

- Role-based access (admin vs. staff) and a full audit log of every change.
- OCR for scanned documents (for example Tesseract, which is free).
- Local sentence embeddings (for example `sentence-transformers/all-MiniLM-L6-v2`) for better policy search.
- Due dates and reminders for cases that are waiting on information.
- Export case summaries as PDF.
- More rejection codes and a small labelled dataset to measure classifier accuracy.

---

*RxResolveAI is an educational demo. All data in this repository is fictional. It is not an official insurance
system and must not be used for real clinical or coverage decisions.*
