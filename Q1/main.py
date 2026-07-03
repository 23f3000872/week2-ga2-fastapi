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

ALLOWED_ORIGINS = [
    "https://app-2wr2p2.example.com"
]

client_buckets = defaultdict(deque)

# ==========================
# CORS
# ==========================

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)

# ==========================
# REQUEST CONTEXT MIDDLEWARE
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
# RATE LIMIT MIDDLEWARE
# ==========================

@app.middleware("http")
async def rate_limit(request: Request, call_next):

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
# PRE-FLIGHT
# ==========================

@app.options("/ping")
async def ping_options():
    return {"ok": True}

# ==========================
# PING
# ==========================

@app.get("/ping")
async def ping(request: Request):

    return {
        "email": EMAIL,
        "request_id": request.state.request_id
    }