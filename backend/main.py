"""
RxResolveAI — FastAPI application entry point.

Run with:
    uvicorn main:app --reload

Interactive API docs are available at http://localhost:8000/docs
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import config
from database import SessionLocal, init_db
from routers import auth_routes, cases, dashboard, documents, policies
from seed import seed_demo_data

logger = logging.getLogger("rxresolveai")

DISCLAIMER = (
    "RxResolveAI provides AI-assisted administrative guidance. All recommendations and generated "
    "documents must be reviewed by authorized staff before use."
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs once when the server starts.
    init_db()
    if config.SEED_DEMO_DATA:
        db = SessionLocal()
        try:
            seed_demo_data(db)
        finally:
            db.close()
    yield


app = FastAPI(
    title="RxResolveAI API",
    description="AI-assisted administrative decision support for prescription claim rejections. " + DISCLAIMER,
    version="1.0.0",
    lifespan=lifespan,
)

# The Vite dev server proxies /api, but CORS is enabled too in case the frontend runs elsewhere locally.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unexpected_error_handler(request: Request, error: Exception):
    """Return a friendly JSON error instead of crashing on unexpected problems."""
    logger.exception("Unexpected error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Unexpected server error. Please try again or check the server log."})


app.include_router(auth_routes.router)
app.include_router(dashboard.router)
app.include_router(cases.router)
app.include_router(documents.router)
app.include_router(policies.router)


@app.get("/", tags=["system"])
def root():
    """Opening http://localhost:8000 in a browser shows this instead of "Not Found"."""
    return {
        "message": "RxResolveAI API is running. Open the web app at http://localhost:5173 (start it with: npm run dev).",
        "api_docs": "http://localhost:8000/docs",
        "health": "http://localhost:8000/api/health",
    }


@app.get("/api/health", tags=["system"])
def health():
    return {"status": "ok", "disclaimer": DISCLAIMER}
