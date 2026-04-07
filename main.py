from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import time
import os
from dotenv import load_dotenv

from database import engine, Base
from routers import auth, tickets, admin, ai_assistant

load_dotenv()

# ─── Logging Setup ───────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("app.log"),
    ]
)
logger = logging.getLogger(__name__)

# ─── DB Init ─────────────────────────────────────────────────────────────────────
Base.metadata.create_all(bind=engine)

# ─── App ─────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Ticket Management System",
    description="""
A full-featured ticket management API with:
- JWT-based authentication (User & Admin roles)
- Full ticket CRUD with filters, search, sorting
- Admin dashboard with stats and pagination
- AI-powered ticket assistant (OpenAI GPT-4o-mini)
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Request Logging Middleware ───────────────────────────────────────────────────
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = round((time.time() - start) * 1000, 2)
    logger.info(
        f"{request.method} {request.url.path} → {response.status_code} ({duration}ms)"
    )
    return response


# ─── Global Exception Handler ─────────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error on {request.method} {request.url.path}: {exc}")
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# ─── Routers ─────────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(tickets.router)
app.include_router(admin.router)
app.include_router(ai_assistant.router)


@app.get("/", tags=["Health"])
def root():
    return {
        "message": "Ticket Management System API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}
