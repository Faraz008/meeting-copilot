import re

PAST = re.compile(
    r"\b(?:i|we|he|she|they)(?:'ve|'d)?\s+(?:(?:already|just|have|had|finally)\s+)*"
    r"(?:sent|finished|fixed|shipped|merged|booked|completed|updated|pushed|deployed|"
    r"emailed|submitted|resolved|wrote|checked|reviewed|did)\b",
    re.I,
)
FUTURE = re.compile(
    r"(\bwill\b|'ll\b|\bgoing to\b|\bgonna\b|\bneed to\b|\bhave to\b|\btomorrow\b|\btonight\b|"
    r"\bnext\b|\blater\b|\bby\b|\bbefore\b|\buntil\b|\b(?:mon|tues|wednes|thurs|fri)day\b|"
    r"\bcan you\b|\bcould you\b|\bplease\b)",
    re.I,
)


def looks_completed(text: str) -> bool:
    """True only when the text reports finished work and contains no forward-looking cue."""
    return bool(PAST.search(text)) and not FUTURE.search(text)
