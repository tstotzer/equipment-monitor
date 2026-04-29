import threading
import time
from typing import Optional

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from simulator import NORMAL_PARAMS, run_simulation
from agent import run_analysis

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/")
def serve_frontend():
    return FileResponse("frontend/index.html")

app = FastAPI(title="Pump Monitor API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Normal ranges derived from simulator NORMAL_PARAMS (mean ± 2*std).
# These match the actual values the simulator generates.
TAG_RANGES: dict[str, tuple[float, float]] = {
    tag: (p["mean"] - 2 * p["std"], p["mean"] + 2 * p["std"])
    for tag, p in NORMAL_PARAMS.items()
}

TAGS = list(NORMAL_PARAMS.keys())

# Sim-minutes of data revealed per real second (controls playback speed).
PLAYBACK_SPEED = 10


def tag_status(tag: str, value: float) -> str:
    if tag not in TAG_RANGES:
        return "green"
    lo, hi = TAG_RANGES[tag]
    margin = 0.15 * (hi - lo)
    if lo <= value <= hi:
        return "green"
    elif (lo - margin) <= value <= (hi + margin):
        return "yellow"
    else:
        return "red"


class SimState:
    def __init__(self):
        self.df: Optional[pd.DataFrame] = None
        self.cursor: int = 0
        self.is_running: bool = False
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None


state = SimState()


class StartRequest(BaseModel):
    fault_type: str = "none"
    fault_start: int = 240
    duration: int = 480


@app.post("/start")
def start_simulation(req: StartRequest):
    # Stop any in-progress simulation
    state._stop.set()
    if state._thread and state._thread.is_alive():
        state._thread.join(timeout=3)
    state._stop.clear()

    fault_type = None if req.fault_type == "none" else req.fault_type
    duration = max(1, min(req.duration, 5600))

    def worker():
        df = run_simulation(fault_type=fault_type, fault_start=req.fault_start, duration=duration)
        total = len(df)

        with state._lock:
            state.df = df
            state.cursor = 0
            state.is_running = True

        # _stop.wait() returns True immediately when stop is called,
        # instead of sleeping the full second before checking.
        while not state._stop.wait(timeout=1.0):
            with state._lock:
                state.cursor = min(state.cursor + PLAYBACK_SPEED, total)
                if state.cursor >= total:
                    state.is_running = False
                    break

    state._thread = threading.Thread(target=worker, daemon=True)
    state._thread.start()

    return {"status": "started", "fault_type": req.fault_type, "fault_start": req.fault_start}


@app.get("/tags")
def get_tags():
    with state._lock:
        if state.df is None or state.cursor == 0:
            return {"tags": {}, "time": None, "is_running": False}
        row = state.df.iloc[state.cursor - 1]
        is_running = state.is_running

    tags = {
        tag: {"value": round(float(row[tag]), 4), "status": tag_status(tag, float(row[tag]))}
        for tag in TAGS
        if tag in row.index
    }
    return {"tags": tags, "time": float(row["time"]), "is_running": is_running}


@app.get("/history")
def get_history():
    with state._lock:
        if state.df is None or state.cursor == 0:
            return {"history": {}, "is_running": False, "total": 0}
        subset = state.df.iloc[: state.cursor].copy()
        is_running = state.is_running
        total = len(state.df)

    return {"history": subset.to_dict(orient="list"), "is_running": is_running, "total": total}


@app.post("/analyze")
def analyze():
    with state._lock:
        if state.df is None or state.cursor < 30:
            raise HTTPException(
                status_code=400,
                detail="Need at least 30 data points. Start a simulation first."
            )
        subset = state.df.iloc[: state.cursor].copy()

    diagnosis = run_analysis(subset)
    return {"diagnosis": diagnosis}


@app.post("/stop")
def stop_simulation():
    state._stop.set()
    with state._lock:
        state.is_running = False
    return {"status": "stopped"}
