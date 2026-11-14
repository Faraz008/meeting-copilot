import json
import re


class JSONParseError(ValueError): ...


FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.S | re.I)


def extract_json(text: str):
    text = text.strip()
    m = FENCE.search(text)
    if m:
        text = m.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    a, b = text.find("{"), text.rfind("}")
    if a == -1 or b <= a:
        raise JSONParseError("no JSON object found")
    cand = text[a : b + 1]
    err = None
    for attempt in (cand, re.sub(r",\s*([}\]])", r"\1", cand)):  # trailing commas
        try:
            return json.loads(attempt)
        except json.JSONDecodeError as e:
            err = e
    raise JSONParseError(f"invalid JSON: {err}")
