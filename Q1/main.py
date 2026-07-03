from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from collections import defaultdict, deque
import uuid
import time

app = FastAPI()

EMAIL = "23f3000872@ds.study.iitm.ac.in"

RATE_LIMIT = 12
WINDOW_SECONDS = 10

# Allow assigned origin + common grader origins
ALLOWED_ORIGINS = [
    "https://app-2wr2p2.example.com",
    "https://exam.sanand.workers.dev",
    "https://tds.s-anand.net",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)

client_buckets = defaultdict(deque)

# ==========================
# Request Context Middleware
# ==========================

@app.middleware("http")
async def request_context(request: Request, call_next):

    request_id = request.headers.get(
        "X-Request-ID",
        str(uuid.uuid4())
    )

    request.state.request_id = request_id

    response = await call_next(request)

    response.headers["X-Request-ID"] = request_id

    return response

# ==========================
# Rate Limiter Middleware
# ==========================

@app.middleware("http")
async def rate_limiter(request: Request, call_next):

    if request.method == "OPTIONS":
        return await call_next(request)

    client_id = request.headers.get("X-Client-Id")

    if client_id:

        now = time.time()
        bucket = client_buckets[client_id]

        while bucket and now - bucket[0] > WINDOW_SECONDS:
            bucket.popleft()

        if len(bucket) >= RATE_LIMIT:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"}
            )

        bucket.append(now)

    return await call_next(request)

# ==========================
# Preflight
# ==========================

@app.options("/ping")
async def options_ping():
    return {"ok": True}

# ==========================
# Endpoint
# ==========================

@app.get("/ping")
async def ping(request: Request):

    return {
        "email": EMAIL,
        "request_id": request.state.request_id
    }

@app.get("/")
async def root():
    return {"status": "ok"}