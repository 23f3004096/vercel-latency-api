# api/index.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pathlib import Path
import numpy as np
import pandas as pd
import json

app = FastAPI()

# Standard middleware (keeps things clean)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],            # allow any origin (required by exam)
    allow_credentials=True,
    allow_methods=["*"],            # allow POST and OPTIONS etc.
    allow_headers=["*"],
    expose_headers=["*"],
)

# Explicit CORS headers to attach to responses (double-safety)
CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "*",
    # Optional:
    "Access-Control-Max-Age": "3600",
}

# Load telemetry once (file is in the same folder as index.py)
DATA_PATH = Path(__file__).parent / "q-vercel-latency.json"
if not DATA_PATH.exists():
    # Fail early with a helpful message in the logs
    raise FileNotFoundError(f"{DATA_PATH} not found. Make sure q-vercel-latency.json is at repo root alongside api/.")
with open(DATA_PATH, "r") as fh:
    telemetry = pd.DataFrame(json.load(fh))


def make_region_result(df_region, threshold):
    """Return aggregated metrics for a DataFrame filtered to one region."""
    if df_region.empty:
        return {
            "avg_latency": None,
            "p95_latency": None,
            "avg_uptime": None,
            "breaches": 0,
        }
    avg_latency = df_region["latency_ms"].mean()
    p95_latency = float(np.percentile(df_region["latency_ms"], 95))
    avg_uptime = df_region["uptime_pct"].mean()
    breaches = int((df_region["latency_ms"] > threshold).sum())
    return {
        "avg_latency": round(float(avg_latency), 2),
        "p95_latency": round(p95_latency, 2),
        "avg_uptime": round(float(avg_uptime), 3),
        "breaches": breaches,
    }


# --- Preflight handlers (explicit) ---
# Respond to OPTIONS on root and /api with the CORS headers.
@app.options("/")
async def options_root():
    return Response(status_code=204, headers=CORS_HEADERS)


@app.options("/api")
async def options_api():
    return Response(status_code=204, headers=CORS_HEADERS)


# Also provide a small GET so visiting the URL in a browser won't crash
@app.get("/")
async def home():
    return JSONResponse({"status": "ok", "message": "POST JSON to / or /api"}, headers=CORS_HEADERS)


@app.get("/api")
async def home_api():
    return JSONResponse({"status": "ok", "message": "POST JSON to / or /api"}, headers=CORS_HEADERS)


# --- Main POST handler (accepts requests at both / and /api) ---
@app.post("/")
async def latency_root(request: Request):
    return await _handle_post(request)


@app.post("/api")
async def latency_api(request: Request):
    return await _handle_post(request)


async def _handle_post(request: Request):
    """Shared logic for handling POST to / or /api"""
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400, headers=CORS_HEADERS)

    regions = payload.get("regions", [])
    threshold = payload.get("threshold_ms", 0)

    if not isinstance(regions, (list, tuple)):
        return JSONResponse({"error": "regions must be a list"}, status_code=400, headers=CORS_HEADERS)

    result = {}
    for region in regions:
        df_region = telemetry[telemetry["region"] == region]
        result[region] = make_region_result(df_region, threshold)

    # Return JSON with CORS headers explicitly attached
    return JSONResponse(result, headers=CORS_HEADERS)
