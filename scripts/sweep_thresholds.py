import sys

from copilot.eval.runner import RunSpec, load_scores, run_system
from copilot.eval.score import ScoreConfig, aggregate, metrics
from copilot.tuning import TUNE, override

GRID = {
    "dedupe_title": [70, 80, 90],
    "supersede_hint": [60, 70, 80],
    "supersede_cue": [75, 85, 95],
    "grounding": [75, 85, 92],
}


def format_metric(m: dict, k: str) -> str:
    return f"{(m[k] or 0) * 100:5.0f}%"


def main(provider: str, prompt: str = "extract_v1"):
    print(f"{'param':16} {'value':>6} | act F1 | full-correct | dec F1 | unres-Q R | ungrounded")

    for param, values in GRID.items():
        for v in values:
            with override(**{param: v}):
                name = f"sweep__{param}_{v}"

                run_system(
                    RunSpec(
                        name=name,
                        provider=provider,
                        cache_mode="live",
                        pipeline={"extract_prompt": prompt},
                    )
                )

                m = metrics(aggregate(load_scores(name, "dev", ScoreConfig())))

            star = "*" if getattr(TUNE, param) == v else " "

            print(
                f"{param:16} {v:>5}{star} | "
                f"{format_metric(m, 'act_f1')} | "
                f"{format_metric(m, 'act_full_recall')}       | "
                f"{format_metric(m, 'dec_f1')} | "
                f"{format_metric(m, 'q_unres_recall')}    | "
                f"{format_metric(m, 'ungrounded_rate')}"
            )


if __name__ == "__main__":
    main(*sys.argv[1:3])
