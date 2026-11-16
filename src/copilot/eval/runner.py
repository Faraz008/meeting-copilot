import json
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

from copilot.eval.baseline import run_baseline
from copilot.eval.pred import Prediction, from_extraction
from copilot.eval.score import MeetingScore, ScoreConfig, score_meeting
from copilot.extract.pipeline import PipelineConfig, run_pipeline
from copilot.extract.prompts import load_prompt
from copilot.io import ROOT, load_meeting
from copilot.llm.factory import build_router

RUNS = ROOT / "data/runs/eval"


@dataclass
class RunSpec:
    name: str
    system: str = "pipeline"
    split: str = "dev"
    provider: str | None = None
    cache_mode: str = "live"
    cache_dir: str | None = None
    log: bool = True
    resume: bool = False
    limit: int | None = None
    baseline_prompt: str = "baseline_v1"
    pipeline: dict = field(default_factory=dict)
    max_attempts: int = 4


def git_info() -> dict:
    def sh(*a):
        try:
            return subprocess.run(
                a,
                capture_output=True,
                text=True,
                cwd=ROOT,
                timeout=10,
            ).stdout.strip()
        except Exception:
            return ""

    return {
        "sha": sh("git", "rev-parse", "--short", "HEAD"),
        "dirty": bool(sh("git", "status", "--porcelain")),
    }


def gold_paths(split: str) -> list[Path]:
    return sorted((ROOT / "data/gold" / split).glob("*.json"))


def run_system(spec: RunSpec) -> Path:
    out = RUNS / spec.name
    out.mkdir(parents=True, exist_ok=True)

    router = build_router(
        order=[spec.provider] if spec.provider else None,
        cache_mode=spec.cache_mode,
        run_id=spec.name,
        log=spec.log,
        cache_dir=spec.cache_dir,
        max_attempts=spec.max_attempts,
    )

    cfg = PipelineConfig(**spec.pipeline)
    done = []

    for gp in gold_paths(spec.split)[: spec.limit]:
        try:
            meeting, g = load_meeting(gp)
        except FileNotFoundError as e:
            print(f"skip {gp.name}: transcript missing ({e.filename})")
            continue

        pf = out / f"{g.meeting_id}.pred.json"
        done.append(g.meeting_id)

        if spec.resume and pf.exists():
            continue

        t0 = time.time()

        try:
            if spec.system == "baseline":
                pred = run_baseline(
                    meeting,
                    router,
                    spec.baseline_prompt,
                )
            else:
                ro = run_pipeline(meeting, router, cfg)
                pred = from_extraction(
                    g.meeting_id,
                    spec.name,
                    ro.result,
                    ro.report,
                )

        except Exception as e:
            pred = Prediction(
                meeting_id=g.meeting_id,
                system=spec.name,
                ok=False,
                error=f"{type(e).__name__}: {e}"[:300],
            )

        pred.report["wall_s"] = round(time.time() - t0, 1)
        pf.write_text(
            pred.model_dump_json(indent=1),
            encoding="utf-8",
        )

        flag = "ok" if pred.ok and pred.report.get("complete", True) else "INCOMPLETE"

        print(
            f"{spec.name} {g.meeting_id}: "
            f"{len(pred.actions)} actions "
            f"{pred.report['wall_s']}s {flag}"
        )

    manifest = {
        "name": spec.name,
        "system": spec.system,
        "split": spec.split,
        "provider": spec.provider,
        "models": [(p.name, p.model) for p in router.providers],
        "cache_mode": spec.cache_mode,
        "pipeline": spec.pipeline,
        "max_attempts": spec.max_attempts,
        "baseline_prompt": spec.baseline_prompt,
        "meetings": done,
        "prompt_sha": (
            load_prompt(cfg.extract_prompt).sha
            if spec.system == "pipeline"
            else load_prompt(spec.baseline_prompt).sha
        ),
        "git": git_info(),
        "finished": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    (out / "manifest.json").write_text(
        json.dumps(manifest, indent=1),
        encoding="utf-8",
    )

    return out


def load_manifest(name: str) -> dict:
    return json.loads((RUNS / name / "manifest.json").read_text(encoding="utf-8"))


def load_scores(
    name: str,
    split: str,
    cfg: ScoreConfig,
) -> list[MeetingScore]:
    d, out = RUNS / name, []

    for gp in gold_paths(split):
        try:
            meeting, g = load_meeting(gp)
        except FileNotFoundError:
            continue

        pf = d / f"{g.meeting_id}.pred.json"

        pred = (
            Prediction.model_validate_json(pf.read_text(encoding="utf-8"))
            if pf.exists()
            else Prediction(
                meeting_id=g.meeting_id,
                system=name,
                ok=False,
                error="missing prediction",
            )
        )

        out.append(score_meeting(g, pred, meeting.turns, cfg))

    return out
