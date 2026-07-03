from fastapi import FastAPI, Header, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from collections import defaultdict, deque
from typing import Optional
import uuid
import time

app = FastAPI()

TOTAL_ORDERS = 51
RATE_LIMIT = 19
WINDOW_SECONDS = 10

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Storage
idempotency_store = {}
client_buckets = defaultdict(deque)

# Rate Limiting Middleware
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
            retry_after = max(
                1,
                int(WINDOW_SECONDS - (now - bucket[0]))
            )

            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"},
                headers={"Retry-After": str(retry_after)}
            )

        bucket.append(now)

    return await call_next(request)


@app.get("/")
def home():
    return {"status": "ok"}


# 1. Idempotent Order Creation
@app.post("/orders", status_code=201)
def create_order(
    idempotency_key: Optional[str] = Header(
        None,
        alias="Idempotency-Key"
    )
):

    if not idempotency_key:
        raise HTTPException(
            status_code=400,
            detail="Missing Idempotency-Key"
        )

    if idempotency_key in idempotency_store:
        return idempotency_store[idempotency_key]

    order = {
        "id": str(uuid.uuid4())
    }

    idempotency_store[idempotency_key] = order

    return order


# 2. Cursor Pagination
@app.get("/orders")
def list_orders(
    limit: int = 10,
    cursor: Optional[str] = None
):

    start = int(cursor) if cursor else 1

    end = min(start + limit - 1, TOTAL_ORDERS)

    items = [
        {"id": i}
        for i in range(start, end + 1)
    ]

    next_cursor = (
        str(end + 1)
        if end < TOTAL_ORDERS
        else None
    )

    return {
        "items": items,
        "next_cursor": next_cursor
    }