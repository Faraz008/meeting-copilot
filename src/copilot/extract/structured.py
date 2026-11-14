from dataclasses import dataclass
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from copilot.llm.base import LLMError
from copilot.llm.jsonutil import JSONParseError, extract_json

T = TypeVar("T", bound=BaseModel)


class OutputTruncated(LLMError): ...


class StructuredFailure(LLMError):
    def __init__(self, attempts: list["Attempt"]):
        super().__init__("; ".join(f"{a.provider}:{a.kind}" for a in attempts) or "no providers")
        self.attempts = attempts


@dataclass
class Attempt:
    provider: str
    kind: str  # ok | invalid_json | schema | llm_error
    detail: str = ""
    repaired: bool = False


def _summarize(e: ValidationError, limit: int = 6) -> str:
    return "; ".join(f"{'.'.join(map(str, x['loc']))}: {x['msg']}" for x in e.errors()[:limit])


def generate_validated(
    router,
    messages: list[dict],
    model_cls: type[T],
    *,
    purpose: str = "extract",
    max_repairs: int = 1,
    max_tokens: int = 4096,
    temperature: float = 0.0,
) -> tuple[T, list[Attempt]]:
    """
    Invalid output: one repair round on the same provider,
    then try the next provider, finally raise StructuredFailure.

    Truncated output raises OutputTruncated so the caller
    can split the input.
    """
    attempts: list[Attempt] = []
    providers = router.available() or (router.wait_until_available() and router.available()) or []
    for p in providers:
        msgs = list(messages)
        for repair in range(max_repairs + 1):
            try:
                comp = router.call(
                    p,
                    msgs,
                    purpose=purpose if repair == 0 else "repair",
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
            except LLMError as e:
                attempts.append(Attempt(p.name, "llm_error", f"{type(e).__name__}: {e}"[:200]))
                break
            if comp.finish_reason == "length":
                raise OutputTruncated(f"{p.name} hit max_tokens={max_tokens}")
            try:
                obj = model_cls.model_validate(extract_json(comp.text))
                attempts.append(Attempt(p.name, "ok", repaired=repair > 0))
                return obj, attempts
            except (JSONParseError, ValidationError) as e:
                kind = "invalid_json" if isinstance(e, JSONParseError) else "schema"
                detail = str(e)[:300] if kind == "invalid_json" else _summarize(e)
                attempts.append(Attempt(p.name, kind, detail))
                if repair < max_repairs:
                    msgs = msgs + [
                        {
                            "role": "assistant",
                            "content": comp.text[:6000],
                        },
                        {
                            "role": "user",
                            "content": (
                                f"Your previous output was invalid: "
                                f"{detail[:600]}\n"
                                "Return the corrected JSON object only, "
                                "no commentary."
                            ),
                        },
                    ]
    raise StructuredFailure(attempts)
