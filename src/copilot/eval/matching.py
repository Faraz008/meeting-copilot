from dataclasses import dataclass

from rapidfuzz import fuzz

from copilot.validate.grounding import norm

DEFAULT_MIN_TITLE = 40.0
DEFAULT_TOL = 1


@dataclass
class Match:
    gold_i: int
    pred_i: int
    score: float
    sim: float


def title_sim(a: str, b: str) -> float:
    a, b = norm(a), norm(b)
    return float(fuzz.token_set_ratio(a, b)) if a and b else 0.0


def near(a: list[int], b: list[int], tol: int = 1) -> bool:
    return any(abs(x - y) <= tol for x in a for y in b)


def _overlap(pred_turns: list[int], gold_turns: list[int], tol: int) -> float:
    if not pred_turns:
        return 0.0
    return sum(any(abs(p - g) <= tol for g in gold_turns) for p in pred_turns) / len(pred_turns)


def match_items(
    g_text,
    g_turns,
    p_text,
    p_turns,
    *,
    use_turns: bool = True,
    min_title: float = DEFAULT_MIN_TITLE,
    tol: int = DEFAULT_TOL,
) -> list[Match]:
    """One-to-one greedy matching by descending score. Deterministic."""
    cands = []
    for gi in range(len(g_text)):
        for pi in range(len(p_text)):
            s = title_sim(g_text[gi], p_text[pi])
            if s < min_title:
                continue
            if use_turns:
                if not near(g_turns[gi], p_turns[pi], tol):
                    continue
                score = 0.7 * s + 30 * _overlap(p_turns[pi], g_turns[gi], tol)
            else:
                score = s
            cands.append((-score, gi, pi, s))
    cands.sort()
    used_g, used_p, out = set(), set(), []
    for neg, gi, pi, s in cands:
        if gi in used_g or pi in used_p:
            continue
        used_g.add(gi)
        used_p.add(pi)
        out.append(Match(gi, pi, -neg, s))
    return out
