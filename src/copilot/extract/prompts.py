import hashlib
import re
from dataclasses import dataclass

from copilot.extract.chunking import Chunk
from copilot.io import ROOT
from copilot.models import Meeting

PROMPT_DIR = ROOT / "prompts"


@dataclass
class Prompt:
    name: str
    system: str
    user: str
    sha: str


def load_prompt(name: str) -> Prompt:
    text = (PROMPT_DIR / f"{name}.md").read_text(encoding="utf-8")
    sys_part, user_part = text.split("<!--USER-->")
    return Prompt(
        name,
        sys_part.replace("<!--SYSTEM-->", "").strip(),
        user_part.strip(),
        hashlib.sha256(text.encode()).hexdigest()[:8],
    )


def render(prompt: Prompt, **vars) -> list[dict]:
    def fill(s: str) -> str:
        for k, v in vars.items():
            s = s.replace(f"<<{k}>>", str(v))
        left = re.findall(r"<<[A-Z_]+>>", s)
        if left:
            raise ValueError(f"unfilled placeholders in prompt {prompt.name}: {left}")
        return s

    return [
        {"role": "system", "content": fill(prompt.system)},
        {"role": "user", "content": fill(prompt.user)},
    ]


def build_extract_messages(prompt: Prompt, meeting: Meeting, chunk: Chunk) -> list[dict]:
    return render(
        prompt,
        MEETING_DATE=meeting.date.isoformat(),
        WEEKDAY=meeting.date.strftime("%A"),
        ROSTER=", ".join(meeting.roster) or "unknown",
        CORE_START=chunk.core_start,
        TRANSCRIPT=chunk.render(),
    )
