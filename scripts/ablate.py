import sys

from copilot.eval.report import PRIMARY, comparison_md
from copilot.eval.runner import RunSpec, load_scores, run_system
from copilot.eval.score import ScoreConfig
from copilot.io import ROOT

VARIANTS = [
    ("baseline", dict(system="baseline")),
    ("full", {}),
    ("no_grounding", dict(pipeline={"use_grounding": False})),
    ("no_code_dates", dict(pipeline={"date_resolver": "dateparser"})),
    ("no_pass2", dict(pipeline={"use_pass2": False})),
    (
        "naive_pipeline",
        dict(
            pipeline={
                "use_grounding": False,
                "use_pass2": False,
                "date_resolver": "dateparser",
            }
        ),
    ),
]

KEYS = [
    (label, k)
    for label, k in PRIMARY
    if k
    in {
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
    }
]


def main(provider: str, prompt: str = "extract_v1", tag: str = ""):
    names = {}

    for label, kw in VARIANTS:
        name = f"{provider}{tag}__{label}"
        pipe = {"extract_prompt": prompt, **kw.pop("pipeline", {})} if label != "baseline" else {}
        run_system(
            RunSpec(
                name=name,
                provider=provider,
                cache_mode="live",
                pipeline=pipe,
                **kw,
            )
        )
        names[label] = name

    cfg_title = ScoreConfig(use_turns=False)
    cfg_turns = ScoreConfig(use_turns=True)

    out = ROOT / "docs/results"
    out.mkdir(parents=True, exist_ok=True)

    head = {label: load_scores(n, "dev", cfg_title) for label, n in names.items()}

    abl = {
        label: load_scores(n, "dev", cfg_turns) for label, n in names.items() if label != "baseline"
    }

    text = (
        "## Baseline vs pipeline (title matcher for both)\n\n"
        + comparison_md(head, "baseline", KEYS, "title")
        + "\n## Pipeline ablations (turn matcher)\n\n"
        + comparison_md(abl, "full", KEYS, "turns")
    )

    (out / f"ablation_{provider}{tag}.md").write_text(
        text,
        encoding="utf-8",
    )

    print(text)


if __name__ == "__main__":
    main(sys.argv[1], *(sys.argv[2:4]))
