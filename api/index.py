from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import numpy as np
import pandas as pd
from pathlib import Path
import json

app = FastAPI()

# ✅ Enable CORS for ALL origins (required for the exam portal)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"]
)

# Load telemetry file once at startup
DATA_PATH = Path(__file__).parent / "q-vercel-latency.json"
with open(DATA_PATH, "r") as f:
    TELEMETRY = pd.DataFrame(json.load(f))


@app.post("/")
async def latency_endpoint(request: Request):
    body = await request.json()
    regions = body.get("regions", [])
    threshold = body.get("threshold_ms", 999999)

    df = TELEMETRY[TELEMETRY["region"].isin(regions)].copy()

    # Compute metrics
    df["breach"] = df["latency_ms"] > threshold

    result = (
        df.groupby("region")
        .agg(
            avg_latency=("latency_ms", "mean"),
            p95_latency=("latency_ms", lambda x: np.percentile(x, 95)),
            avg_uptime=("uptime_pct", "mean"),
            breaches=("breach", "sum")
        )
        .round(3)
        .reset_index()
        .to_dict(orient="records")
    )

    return {"results": result}


@app.options("/")
async def options_handler():
    """Preflight CORS handler"""
    return {"message": "OK"}
