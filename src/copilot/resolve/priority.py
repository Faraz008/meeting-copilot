import re
from datetime import date

HIGH = re.compile(
    r"\b(urgent|asap|critical|blocker|blocking|p0|p1|"
    r"top priority|high priority|immediately|right away)\b",
    re.I,
)

LOW = re.compile(
    r"\b(low priority|nice to have|no rush|whenever|"
    r"when you get a chance|eventually|someday)\b",
    re.I,
)


def priority(text: str, deadline: date | None, base: date) -> str:
    if HIGH.search(text):
        return "high"
    if LOW.search(text):
        return "low"
    if deadline and (deadline - base).days <= 1:
        return "high"
    return "normal"
