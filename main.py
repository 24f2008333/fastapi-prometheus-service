
import json
import logging
import time
import uuid
from collections import deque
from datetime import datetime, timezone

from fastapi import FastAPI, Query, Request
from fastapi.responses import Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST

app = FastAPI()
started = time.monotonic()

requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests"
)

logs = deque(maxlen=1000)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("service")


@app.middleware("http")
async def track_requests(request: Request, call_next):
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    ts = datetime.now(timezone.utc).isoformat()
    start = time.monotonic()
    status_code = 500

    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        entry = {
            "level": "info",
            "ts": ts,
            "path": request.url.path,
            "request_id": request_id,
            "method": request.method,
            "status_code": status_code,
            "duration_ms": round((time.monotonic() - start) * 1000, 2),
        }
        requests_total.inc()
        logs.append(entry)
        logger.info(json.dumps(entry))


@app.get("/work")
async def work(n: int = Query(default=1, ge=0, le=1000000)):
    for i in range(n):
        _ = i * i
    return {
        "email": "service@example.com",
        "done": n
    }


@app.get("/metrics")
async def metrics():
    return Response(
        generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


@app.get("/healthz")
async def healthz():
    return {
        "status": "ok",
        "uptime_s": float(max(0, time.monotonic() - started))
    }


@app.get("/logs/tail")
async def logs_tail(limit: int = Query(default=100, ge=1, le=1000)):
    return list(logs)[-limit:]
