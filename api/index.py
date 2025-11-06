from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import json
import numpy as np
import pandas as pd
from pathlib import Path

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST"],
    allow_headers=["*"],
)

DATA_PATH = Path(__file__).parent / "q-vercel-latency.json"
df = pd.read_json(DATA_PATH)


@app.post("/")
async def latency_report(request: Request):
    payload = await request.json()
    regions = payload.get("regions", [])
    threshold = payload.get("threshold_ms", 0)

    result = {}

    for region in regions:
        sub = df[df["region"] == region]
        if sub.empty:
            continue

        avg_latency = sub["latency_ms"].mean()
        p95_latency = np.percentile(sub["latency_ms"], 95)
        avg_uptime = sub["uptime_pct"].mean()
        breaches = (sub["latency_ms"] > threshold).sum()

        result[region] = {
            "avg_latency": round(avg_latency, 2),
            "p95_latency": round(p95_latency, 2),
            "avg_uptime": round(avg_uptime, 3),
            "breaches": int(breaches),
        }

    return result
