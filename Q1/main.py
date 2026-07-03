from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from collections import defaultdict, deque
import uuid
import time

app = FastAPI()

EMAIL = "23f3000872@ds.study.iitm.ac.in"

RATE_LIMIT = 12
WINDOW_SECONDS = 10

# =====================================
# CORS
# =====================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://app-2wr2p2.example.com",
        "https://tds.s-anand.net",
        "https://exam.sanand.workers.dev",
        "https://courses.iitm.ac.in"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"]
)

# =====================================
# RATE LIMIT STORAGE
# =====================================

client_buckets = defaultdict(deque)

# =====================================
# REQUEST CONTEXT MIDDLEWARE
# =====================================

@app.middleware("http")
async def request_context(request: Request, call_next):

    request_id = request.headers.get("X-Request-ID")

    if not request_id:
        request_id = str(uuid.uuid4())

    request.state.request_id = request_id

    response = await call_next(request)

    response.headers["X-Request-ID"] = request_id

    return response

# =====================================
# RATE LIMIT MIDDLEWARE
# =====================================

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

# =====================================
# OPTIONS /ping
# =====================================

@app.options("/ping")
async def ping_options():
    return Response(status_code=200)

# =====================================
# GET /ping
# =====================================

@app.get("/ping")
async def ping(request: Request):

    request_id = request.state.request_id

    response = JSONResponse(
        content={
            "email": EMAIL,
            "request_id": request_id
        }
    )

    response.headers["X-Request-ID"] = request_id

    return response

# =====================================
# ROOT
# =====================================

@app.get("/")
async def root():
    return {"status": "ok"}