"""
FastAPI wrapper exposing ViralScriptEnv as an OpenEnv-compliant HTTP server.
Deployed to HuggingFace Spaces on port 7860.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from viral_script_engine.environment.env import ViralScriptEnv
import uvicorn

_ROOT = Path(__file__).parent / "viral_script_engine"
_SCRIPTS_PATH = str(_ROOT / "data" / "test_scripts" / "scripts.json")
_CULTURAL_KB_PATH = str(_ROOT / "data" / "cultural_kb.json")

app = FastAPI(
    title="Viral Script Debugging Engine",
    description="Multi-agent RL environment for improving short-form video scripts",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_envs: dict = {}


class ResetRequest(BaseModel):
    session_id: str
    difficulty: str = "easy"
    options: dict = {}


class StepRequest(BaseModel):
    session_id: str
    action: dict


@app.post("/reset")
def reset(req: ResetRequest):
    env = ViralScriptEnv(
        scripts_path=_SCRIPTS_PATH,
        cultural_kb_path=_CULTURAL_KB_PATH,
        difficulty=req.difficulty,
    )
    obs, info = env.reset(options=req.options)
    _envs[req.session_id] = env
    return {"observation": obs, "info": info}


@app.post("/step")
def step(req: StepRequest):
    env = _envs.get(req.session_id)
    if not env:
        raise HTTPException(404, f"Session {req.session_id} not found. Call /reset first.")
    obs, reward, terminated, truncated, info = env.step(req.action)
    return {
        "observation": obs,
        "reward": reward,
        "terminated": terminated,
        "truncated": truncated,
        "info": info,
    }


@app.get("/state/{session_id}")
def state(session_id: str):
    env = _envs.get(session_id)
    if not env:
        raise HTTPException(404, "Session not found")
    return env.state()


@app.get("/health")
def health():
    return {
        "status": "ok",
        "environment": "ViralScriptDebugEngine",
        "version": "1.0.0",
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7860)
