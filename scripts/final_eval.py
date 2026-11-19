import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FROZEN = json.loads((ROOT / "tests/replay_cache/MANIFEST.json").read_text())["pipeline"]

VARIANTS = [
    ("baseline", dict(system="baseline")),
    ("full", {}),
    ("no_grounding", dict(pipeline={"use_grounding": False})),
    ("no_code_dates", dict(pipeline={"date_resolver": "dateparser"})),
    ("no_pass2", dict(pipeline={"use_pass2": False})),
]

KEYS = [
    "act_f1",
    "act_p",
    "act_r",
    "act_full_recall",
    "act_owner_acc",
    "act_dl_acc",
    "dec_f1",
    "q_unres_recall",
    "ungrounded_rate",
    "neg_fp_per_meeting",
]


def gate() -> None:
    if os.environ.get("ALLOW_TEST") != "1" or "--final" not in sys.argv:
        sys.exit(
            "Refusing: ALLOW_TEST=1 python scripts/final_eval.py <provider> <dev_run_name> --final"
        )

    from copilot.eval.runner import git_info

    log_path = ROOT / "docs/test_access.log"

    with log_path.open("a") as file:
        file.write(
            f"{time.strftime('%F %T')}\t{git_info()['sha']}\tfinal_eval {' '.join(sys.argv[1:])}\n"
        )


def main(provider: str, dev_name: str) -> None:
    gate()

    from copilot.eval.cli import pick_matcher  # noqa: F401
    from copilot.eval.report import (
        PRIMARY,
        cell,
        comparison_md,
    )
    from copilot.eval.runner import (
        RUNS,
        RunSpec,
        load_scores,
        run_system,
    )
    from copilot.eval.score import ScoreConfig

    names = {}

    for label, kw in VARIANTS:
        name = f"final__{provider}__{label}"
        manifest = RUNS / name / "manifest.json"
        done = manifest.exists()

        if done and "--resume" not in sys.argv:
            sys.exit(
                f"{name} already completed. Single-run rule: "
                "do not repeat. (--resume only after a crash.)"
            )

        pipeline_overrides = kw.pop("pipeline", {})

        pipe = {} if label == "baseline" else {**FROZEN, **pipeline_overrides}

        if not done:
            run_system(
                RunSpec(
                    name=name,
                    provider=provider,
                    split="test",
                    cache_mode="live",
                    cache_dir="data/llm_cache_test",
                    resume=True,
                    pipeline=pipe,
                    **kw,
                )
            )

        names[label] = name

    labels = {key: label for label, key in PRIMARY}
    keys = [(labels[key], key) for key in KEYS]

    head = {
        label: load_scores(
            name,
            "test",
            ScoreConfig(use_turns=False),
        )
        for label, name in names.items()
    }

    abl = {
        label: load_scores(
            name,
            "test",
            ScoreConfig(use_turns=True),
        )
        for label, name in names.items()
        if label != "baseline"
    }

    dev = load_scores(
        dev_name,
        "dev",
        ScoreConfig(use_turns=True),
    )

    gap = [
        "| metric | dev | test [95% CI] |",
        "|---|---|---|",
    ]

    for label, key in keys:
        dev_cell = cell(key, dev).split(" [")[0]
        test_cell = cell(key, abl["full"])

        gap.append(f"| {label} | {dev_cell} | {test_cell} |")

    text = (
        f"### Baseline vs pipeline: held-out test, {provider}\n\n"
        + comparison_md(
            head,
            "baseline",
            keys,
            "title",
        )
        + f"\n### Ablations: held-out test, {provider}\n\n"
        + comparison_md(
            abl,
            "full",
            keys,
            "turns",
        )
        + "\n### Dev vs test (full pipeline)\n\n"
        + "\n".join(gap)
        + "\n"
    )

    out = ROOT / "docs"

    (out / f"results_final_{provider}.md").write_text(
        text,
        encoding="utf-8",
    )

    (out / "results_final_table.md").write_text(
        text,
        encoding="utf-8",
    )

    print(text)


if __name__ == "__main__":
    args = [arg for arg in sys.argv[1:] if not arg.startswith("--")]

    main(*args[:2])
