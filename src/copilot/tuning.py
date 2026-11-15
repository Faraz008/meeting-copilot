from contextlib import contextmanager
from dataclasses import dataclass


@dataclass
class Tuning:
    grounding: float = 85.0
    dedupe_title: float = 80.0
    supersede_hint: float = 70.0
    supersede_cue: float = 85.0
    competing_title: float = 80.0


TUNE = Tuning()


@contextmanager
def override(**kw):
    for k in kw:
        if not hasattr(TUNE, k):
            raise KeyError(f"unknown tuning parameter: {k}")
    old = {k: getattr(TUNE, k) for k in kw}
    try:
        for k, v in kw.items():
            setattr(TUNE, k, v)
        yield TUNE
    finally:
        for k, v in old.items():
            setattr(TUNE, k, v)
