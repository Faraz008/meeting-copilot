import re
from dataclasses import dataclass, field

from rapidfuzz import fuzz

from copilot.models import Flag, Turn

FIRST_PERSON = {"i", "me", "myself", "i'll", "ill", "i will"}

GROUP = {
    "we",
    "us",
    "our team",
    "the team",
    "team",
    "everyone",
    "everybody",
    "all",
    "all of us",
    "someone",
    "somebody",
    "anyone",
    "anybody",
    "no one",
    "nobody",
    "who",
    "whoever",
    "you guys",
    "y'all",
    "folks",
    "you",
    "you all",
    "they",
    "them",
    "he",
    "she",
    "him",
    "her",
}

GROUP_START = re.compile(
    r"^(someone|somebody|anyone|anybody|everyone|everybody|"
    r"the team|our team|whoever)\b"
)

NICK_GROUPS = [
    {"robert", "rob", "bob", "bobby", "robbie"},
    {"samantha", "samuel", "sam", "sammy"},
    {"william", "will", "bill", "billy", "liam"},
    {"elizabeth", "liz", "beth", "lizzie", "eliza"},
    {"katherine", "catherine", "kate", "katie", "kat"},
    {"michael", "mike", "mikey"},
    {"alexander", "alexandra", "alex"},
    {"daniel", "dan", "danny"},
    {"david", "dave"},
    {"james", "jim", "jimmy", "jamie"},
    {"jennifer", "jen", "jenny"},
    {"jonathan", "jon", "jonny"},
    {"joseph", "joe", "joey"},
    {"matthew", "matt"},
    {"nicholas", "nick"},
    {"richard", "rick", "rich"},
    {"thomas", "tom", "tommy"},
    {"christopher", "chris"},
    {"anthony", "tony"},
    {"stephen", "steven", "steve"},
    {"benjamin", "ben"},
    {"andrew", "andy", "drew"},
    {"priyanka", "priya"},
]


def _nick_group(name: str) -> set[str]:
    out = {name}

    for group in NICK_GROUPS:
        if name in group:
            out |= group

    return out


def _skeleton(s: str) -> str:
    s = re.sub(r"[^a-z]", "", s.lower())
    s = s[:1] + re.sub(r"[aeiou]", "", s[1:])
    return re.sub(r"(.)\1+", r"\1", s)


def _score(
    raw: str,
    entry: str,
    aliases: list[str],
) -> tuple[float, str]:
    toks = re.findall(r"[a-z']+", entry.lower())

    if not toks:
        return 0, ""

    exact = {
        entry.lower(),
        *toks,
        *(alias.lower() for alias in aliases),
    }

    if raw in exact:
        return 100, "exact"

    if raw in _nick_group(toks[0]) or _nick_group(raw) & set(toks[:1]):
        return 95, "nickname"

    skeleton = _skeleton(raw)

    if len(raw) >= 4 and len(skeleton) >= 3 and skeleton == _skeleton(toks[0]):
        return 90, "phonetic"

    ratio = max(fuzz.ratio(raw, token) for token in [*toks, entry.lower()])

    if ratio >= 85:
        return min(ratio, 89.0), "fuzzy"

    return 0, ""


@dataclass
class OwnerResolution:
    owner: str | None
    flags: list[Flag] = field(default_factory=list)
    method: str = ""
    candidates: list[str] = field(default_factory=list)


def resolve_owner(
    raw: str | None,
    owner_turn_idx: int | None,
    evidence_turns: list[int],
    turns: list[Turn],
    roster: list[str],
    aliases: dict[str, list[str]] | None = None,
) -> OwnerResolution:
    aliases = aliases or {}

    raw_name = (raw or "").strip().lower().strip(".,!?")

    if not raw_name:
        return OwnerResolution(
            None,
            [Flag.NO_OWNER],
            "none",
        )

    # First-person owner resolution
    if raw_name in FIRST_PERSON:
        if owner_turn_idx is not None and 0 <= owner_turn_idx < len(turns):
            speaker = turns[owner_turn_idx].speaker

            return OwnerResolution(
                speaker,
                [] if speaker else [Flag.NO_OWNER],
                "first_person" if speaker else "unlabeled",
            )

        speakers = sorted(
            {
                turns[index].speaker
                for index in evidence_turns
                if (0 <= index < len(turns) and turns[index].speaker)
            }
        )

        if len(speakers) == 1:
            return OwnerResolution(
                speakers[0],
                [Flag.LOW_CONFIDENCE],
                "first_person_fallback",
            )

        return OwnerResolution(
            None,
            [Flag.AMBIGUOUS_OWNER],
            "first_person_unclear",
            speakers,
        )

    # Group ownership resolution
    if raw_name in GROUP or GROUP_START.match(raw_name):
        return OwnerResolution(
            None,
            [Flag.NO_OWNER],
            "group_word",
        )

    # Match the owner against the roster
    scored = sorted(
        (
            (score, entry, method)
            for entry in roster
            for score, method in [
                _score(
                    raw_name,
                    entry,
                    aliases.get(entry, []),
                )
            ]
            if score > 0
        ),
        reverse=True,
    )

    if not scored:
        return OwnerResolution(
            None,
            [Flag.NO_OWNER],
            "unknown_name",
        )

    best = scored[0]

    close = [entry for score, entry, _ in scored if best[0] - score < 5]

    if len(close) > 1:
        return OwnerResolution(
            None,
            [Flag.AMBIGUOUS_OWNER],
            "ambiguous_name",
            close,
        )

    flags = [Flag.LOW_CONFIDENCE] if best[2] in ("phonetic", "fuzzy") else []

    return OwnerResolution(
        best[1],
        flags,
        best[2],
    )
