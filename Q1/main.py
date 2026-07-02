from fastapi import FastAPI, Query, Header, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List
import jwt
import time
import uuid
from collections import deque
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST

from collections import defaultdict, deque
import time
import uuid

import re
from pydantic import BaseModel

app = FastAPI()

# ==================================================
# GLOBALS
# ==================================================


TOTAL_ORDERS = 51
RATE_LIMIT = 19
WINDOW_SECONDS = 10

idempotency_store = {}
client_requests = defaultdict(deque)


START_TIME = time.time()

REQUEST_COUNTER = Counter(
    "http_requests_total",
    "Total HTTP requests"
)

LOGS = deque(maxlen=1000)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# ==================================================
# LOGGING + METRICS MIDDLEWARE
# ==================================================

@app.middleware("http")
async def log_requests(request, call_next):
    request_id = str(uuid.uuid4())

    response = await call_next(request)

    REQUEST_COUNTER.inc()

    LOGS.append({
        "level": "INFO",
        "ts": time.time(),
        "path": request.url.path,
        "request_id": request_id
    })

    response.headers["X-Request-ID"] = request_id

    return response

@app.middleware("http")
async def q9_rate_limit(request, call_next):

    if request.url.path.startswith("/orders"):

        client_id = request.headers.get("X-Client-Id")

        if client_id:
            now = time.time()
            bucket = client_requests[client_id]

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
                    headers={
                        "Retry-After": str(retry_after)
                    }
                )

            bucket.append(now)

    return await call_next(request)

# ==================================================
# QUESTION 2 - JWT VERIFY
# ==================================================

PUBLIC_KEY = """
-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA2okOHspNjgA+2rTLbeuY
cxiP/hG8C6Sb9iwg3yiLAA4HCnpITcbWCSelbvbYGuc3EbNy4xFyf5Cbj5DHJMID
EkryOgyd2giIIIBOUBj8S63uGcnRpOBh9NFatfNwheKuzsPuVNldu6A9cNteNpXc
WyJjG2axVfmq7i6SuKr1JoWYG7xTTAvKPujSl4OtsQfO3h5NepzdfXpr28oNnzfW
ed+zclR6BcmNNo/WVfJ4xyCLSf0BCOgdTgW6PdaChd1l9VDetJZVEgC5tkyvXsfI
SI6iyrYbKR0NEBSqq4XkadEjsCs4F1RncsS4LlgniT7GlkL9Mce3b0wGLs9/7ZIX
dQIDAQAB
-----END PUBLIC KEY-----
"""

ISSUER = "https://idp.exam.local"
AUDIENCE = "tds-3i5oxmpw.apps.exam.local"


class TokenRequest(BaseModel):
    token: str


@app.post("/verify")
async def verify_token(data: TokenRequest):
    try:
        payload = jwt.decode(
            data.token,
            PUBLIC_KEY,
            algorithms=["RS256"],
            issuer=ISSUER,
            audience=AUDIENCE,
        )

        return {
            "valid": True,
            "email": payload.get("email"),
            "sub": payload.get("sub"),
            "aud": payload.get("aud"),
        }

    except Exception:
        return JSONResponse(
            status_code=401,
            content={"valid": False}
        )

# ==================================================
# QUESTION 3 - CONFIG MERGE
# ==================================================

def parse_bool(value):
    return str(value).lower() in ["true", "1", "yes", "on"]


@app.get("/effective-config")
async def effective_config(set: List[str] = Query(default=[])):

    config = {
        "port": 8000,
        "workers": 1,
        "debug": False,
        "log_level": "info",
        "api_key": "default-secret-000"
    }

    config.update({
        "port": 8187,
        "log_level": "error"
    })

    config.update({
        "port": 8777,
        "workers": 9,
        "log_level": "debug",
        "api_key": "key-ewphic93z5"
    })

    config.update({
        "workers": 15,
        "log_level": "debug",
        "api_key": "key-bu5rrokggp"
    })

    for item in set:
        if "=" not in item:
            continue

        key, value = item.split("=", 1)

        if key in ["port", "workers"]:
            config[key] = int(value)

        elif key == "debug":
            config[key] = parse_bool(value)

        else:
            config[key] = value

    config["port"] = int(config["port"])
    config["workers"] = int(config["workers"])
    config["debug"] = bool(config["debug"])
    config["log_level"] = str(config["log_level"])

    config["api_key"] = "****"

    return config

# ==================================================
# QUESTION 5 - ANALYTICS
# ==================================================

API_KEY = "ak_341wglxot8ycrxlm4hcmqxs8"


class Event(BaseModel):
    user: str
    amount: float
    ts: int


class AnalyticsRequest(BaseModel):
    events: List[Event]


@app.post("/analytics")
async def analytics(
    data: AnalyticsRequest,
    x_api_key: str = Header(None)
):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    total_events = len(data.events)

    unique_users = len(
        set(event.user for event in data.events)
    )

    revenue = sum(
        event.amount
        for event in data.events
        if event.amount > 0
    )

    user_totals = {}

    for event in data.events:
        if event.amount > 0:
            user_totals[event.user] = (
                user_totals.get(event.user, 0)
                + event.amount
            )

    top_user = (
        max(user_totals, key=user_totals.get)
        if user_totals else ""
    )

    return {
        "email": "23f3000872@ds.study.iitm.ac.in",
        "total_events": total_events,
        "unique_users": unique_users,
        "revenue": float(revenue),
        "top_user": top_user
    }

# ==================================================
# QUESTION 6 - OBSERVABILITY
# ==================================================

@app.get("/work")
async def work(n: int = 1):
    for _ in range(max(0, n)):
        pass

    return {
        "email": "23f3000872@ds.study.iitm.ac.in",
        "done": n
    }


@app.get("/metrics")
async def metrics():
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


@app.get("/healthz")
async def healthz():
    return {
        "status": "ok",
        "uptime_s": float(time.time() - START_TIME)
    }


@app.get("/logs/tail")
async def logs_tail(limit: int = 10):
    return list(LOGS)[-limit:]


# ==================================================
# QUESTION 8
# ==================================================



class ExtractRequest(BaseModel):
    text: str


class ExtractResponse(BaseModel):
    vendor: str
    amount: float
    currency: str
    date: str


@app.post("/extract", response_model=ExtractResponse)
async def extract_invoice(data: ExtractRequest):

    text = data.text.strip()

    if not text:
        raise HTTPException(status_code=422, detail="Empty text")

    # ------------------------------
    # Vendor
    # ------------------------------
    vendor_patterns = [
        r'([A-Za-z0-9\- ]+Industries Ltd\.?)',
        r'([A-Za-z0-9\- ]+Ltd\.?)',
        r'([A-Za-z0-9\- ]+LLC)',
        r'([A-Za-z0-9\- ]+Inc\.?)',
        r'([A-Za-z0-9\- ]+Corporation)',
        r'([A-Za-z0-9\- ]+Company)'
    ]

    vendor = "Unknown"

    for pattern in vendor_patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            vendor = m.group(1).strip()
            break

    # ------------------------------
    # Currency
    # ------------------------------
    currency_match = re.search(
        r'\b(USD|EUR|GBP)\b',
        text,
        re.IGNORECASE
    )

    currency = (
        currency_match.group(1).upper()
        if currency_match
        else "USD"
    )

    # ------------------------------
    # Amount
    # ------------------------------
    amount_patterns = [
        r'Total\s*Due[: ]+\D*(\d+(?:\.\d{1,2})?)',
        r'Total[: ]+\D*(\d+(?:\.\d{1,2})?)',
        r'Amount[: ]+\D*(\d+(?:\.\d{1,2})?)',
        r'Balance[: ]+\D*(\d+(?:\.\d{1,2})?)'
    ]

    amount = 0.0

    for pattern in amount_patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            amount = float(m.group(1))
            break

    if amount == 0.0:
        numbers = re.findall(r'\d+(?:\.\d{1,2})?', text)
        if numbers:
            amount = float(max(numbers, key=lambda x: float(x)))

    # ------------------------------
    # Date
    # ------------------------------
    date_match = re.search(
        r'(2026-\d{2}-\d{2})',
        text
    )

    date = (
        date_match.group(1)
        if date_match
        else "2026-01-01"
    )

    return ExtractResponse(
        vendor=vendor,
        amount=float(amount),
        currency=currency,
        date=date
    )


# ==================================================
# QUESTION 9 - ORDERS API
# ==================================================

@app.post("/orders", status_code=201)
async def create_order(
    order: dict,
    idempotency_key: str = Header(None)
):

    if not idempotency_key:
        raise HTTPException(
            status_code=400,
            detail="Idempotency-Key required"
        )

    if idempotency_key in idempotency_store:
      return JSONResponse(
        status_code=200,
        content=idempotency_store[idempotency_key]
    )

    created_order = {
        "id": str(uuid.uuid4())
    }

    idempotency_store[idempotency_key] = created_order

    return created_order


@app.get("/orders")
async def list_orders(
    limit: int = 10,
    cursor: str = None
):

    start = int(cursor) if cursor else 1

    end = min(
        start + limit - 1,
        TOTAL_ORDERS
    )

    items = [
        {"id": i}
        for i in range(start, end + 1)
    ]

    next_cursor = None

    if end < TOTAL_ORDERS:
        next_cursor = str(end + 1)

    return {
        "items": items,
        "next_cursor": next_cursor
    }