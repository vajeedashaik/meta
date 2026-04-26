"""
OpenEnv-compliant client for ViralScriptEnv.
This is what external users and the training script should use
when connecting to a deployed Space.

Never import from environment.env or any server-side module here.
"""

import requests
import uuid
from typing import Tuple, Optional


class ViralScriptEnvClient:
    """
    HTTP client for the deployed ViralScriptEnv Space.
    Drop-in replacement for ViralScriptEnv when working with a remote deployment.
    Implements the same reset/step/state interface.
    """

    def __init__(self, base_url: str = "http://localhost:7860", timeout: int = 60):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session_id = f"client-{uuid.uuid4().hex[:8]}"

    def reset(self, difficulty: str = "easy", options: dict = None) -> Tuple[dict, dict]:
        r = requests.post(
            f"{self.base_url}/reset",
            json={"session_id": self.session_id, "difficulty": difficulty, "options": options or {}},
            timeout=self.timeout,
        )
        r.raise_for_status()
        data = r.json()
        return data["observation"], data["info"]

    def step(self, action: dict) -> Tuple[dict, float, bool, bool, dict]:
        r = requests.post(
            f"{self.base_url}/step",
            json={"session_id": self.session_id, "action": action},
            timeout=self.timeout,
        )
        r.raise_for_status()
        d = r.json()
        return d["observation"], float(d["reward"]), bool(d["terminated"]), bool(d["truncated"]), d["info"]

    def state(self) -> dict:
        r = requests.get(f"{self.base_url}/state/{self.session_id}", timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def new_session(self):
        """Generate a new session ID — call this before each fresh episode."""
        self.session_id = f"client-{uuid.uuid4().hex[:8]}"
