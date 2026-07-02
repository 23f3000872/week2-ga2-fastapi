from fastapi import FastAPI, Query, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List
import jwt

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

    # config.development.yaml
    config.update({
        "port": 8187,
        "log_level": "error"
    })

    # .env
    config.update({
        "port": 8777,
        "workers": 9,
        "log_level": "debug",
        "api_key": "key-ewphic93z5"
    })

    # OS env
    config.update({
        "workers": 15,
        "log_level": "debug",
        "api_key": "key-bu5rrokggp"
    })

    # CLI overrides
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

    events = data.events

    total_events = len(events)

    unique_users = len(set(event.user for event in events))

    revenue = sum(
        event.amount
        for event in events
        if event.amount > 0
    )

    user_totals = {}

    for event in events:
        if event.amount > 0:
            user_totals[event.user] = (
                user_totals.get(event.user, 0)
                + event.amount
            )

    top_user = max(user_totals, key=user_totals.get) if user_totals else ""

    return {
        "email": "23f3000872@ds.study.iitm.ac.in",
        "total_events": total_events,
        "unique_users": unique_users,
        "revenue": revenue,
        "top_user": top_user
    }