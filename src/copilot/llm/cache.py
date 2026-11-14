import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from copilot.llm.base import CacheMiss, Completion


class CachingProvider:
    """mode: off | live (read-through cache) | replay (cache only; a miss is an error)."""

    def __init__(self, inner, cache_dir: str = "data/llm_cache", mode: str = "live"):
        self.inner, self.mode = inner, mode
        self.name, self.model = inner.name, inner.model
        self.dir = Path(cache_dir)

    def _path(self, messages, json_mode, temperature, max_tokens) -> Path:
        blob = json.dumps(
            {"m": self.model, "msgs": messages, "j": json_mode, "t": temperature, "mt": max_tokens},
            sort_keys=True,
        )
        return self.dir / f"{self.name}__{hashlib.sha256(blob.encode()).hexdigest()[:32]}.json"

    def complete(self, messages, *, json_mode=True, temperature=0.0, max_tokens=2048) -> Completion:
        path = self._path(messages, json_mode, temperature, max_tokens)
        if path.exists():
            return Completion(**{**json.loads(path.read_text("utf-8")), "cached": True})
        if self.mode == "replay":
            raise CacheMiss(f"no recording for {self.name} {path.name}")
        comp = self.inner.complete(
            messages, json_mode=json_mode, temperature=temperature, max_tokens=max_tokens
        )
        self.dir.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({**asdict(comp), "cached": False}), "utf-8")
        return comp
