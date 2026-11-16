import csv
from collections import Counter
from pathlib import Path

from copilot.resolve.tense import looks_completed


def categorize(r: dict) -> list[str]:
    t, k = r["type"], r["kind"]

    if t == "fn":
        if r.get("near_pred"):
            return [f"{k}:matcher_mismatch_or_merged"]

        if k == "action":
            tags = set(r.get("tags", []))

            if r.get("status") == "proposed":
                return ["action:missed_proposal"]

            if tags & {"retraction", "revision"}:
                return ["action:missed_revision_case"]

            return ["action:missed_commitment"]

        return [f"{k}:missed"]

    if t == "fp":
        nearg = r.get("near_gold", [])

        if any(not g["matched"] for g in nearg):
            # Same turns as an unmatched gold item.
            return [f"{k}:matcher_mismatch"]

        if nearg:
            # Same turns as an already-matched gold item.
            return [f"{k}:duplicate_or_split"]

        if k == "action":
            if r.get("status") == "proposed":
                return ["action:extra_proposal"]

            if looks_completed(r.get("quotes", "")):
                return ["action:past_tense_extracted"]

            return ["action:spurious"]

        return [f"{k}:spurious"]

    out = []

    for issue in r["issues"]:
        g, p = r.get("gold", {}), r.get("pred", {})

        if issue == "owner":
            if p.get("owner") is None:
                flags = set(p.get("flags", []))

                out.append(
                    "owner:ambiguous_flagged" if "ambiguous_owner" in flags else "owner:missed"
                )

            elif g.get("owner") in (None, "None"):
                out.append("owner:invented")

            else:
                out.append("owner:wrong_person")

        elif issue == "deadline":
            gd, pd = g.get("deadline"), p.get("deadline")

            if pd in (None, "None"):
                out.append(
                    "deadline:unresolvable_flagged"
                    if "unresolved_deadline" in p.get("flags", [])
                    else "deadline:missing"
                )

            elif gd in (None, "None"):
                out.append("deadline:invented")

            elif gd in p.get("options", []):
                out.append("deadline:ambiguity_primary_wrong")

            else:
                out.append("deadline:wrong_value")

        elif issue == "status":
            out.append(f"status:{g.get('status')}->{p.get('status')}")

        else:
            out.append(f"{r['kind']}:{issue}")

    return out


def write_errors(scores, path: Path) -> Counter:
    path.parent.mkdir(parents=True, exist_ok=True)
    tally: Counter = Counter()

    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)

        w.writerow(
            [
                "meeting",
                "type",
                "kind",
                "auto_category",
                "manual_category",
                "gold_text",
                "pred_text",
                "turns",
                "tags",
                "details",
            ]
        )

        for s in scores:
            for typ in ("fn", "fp", "bad"):
                for r in s.details[typ]:
                    for cat in categorize(r):
                        tally[cat] += 1

                        w.writerow(
                            [
                                s.meeting_id,
                                typ,
                                r["kind"],
                                cat,
                                "",
                                r["text"] if typ != "fp" else "",
                                r.get(
                                    "pred_text",
                                    r["text"] if typ == "fp" else "",
                                ),
                                r.get("turns"),
                                r.get("tags", ""),
                                str(
                                    {
                                        k: r[k]
                                        for k in (
                                            "gold",
                                            "pred",
                                            "quotes",
                                            "near_pred",
                                            "near_gold",
                                        )
                                        if k in r
                                    }
                                ),
                            ]
                        )

    return tally
