from dataclasses import dataclass

from copilot.models import Turn


def render_turn(t: Turn) -> str:
    return f"[{t.idx}] {t.speaker or 'Unknown'}: {t.text}"


@dataclass
class Chunk:
    index: int
    turns: list[Turn]
    core_start: int  # turns before this index are context only

    @property
    def start(self) -> int:
        return self.turns[0].idx

    @property
    def end(self) -> int:
        return self.turns[-1].idx

    def render(self) -> str:
        return "\n".join(render_turn(t) for t in self.turns)


def chunk_turns(turns: list[Turn], max_chars: int = 8000, overlap: int = 4) -> list[Chunk]:
    """Turn-aligned windows. Turn idx must equal list position (parser guarantees this)."""
    chunks: list[Chunk] = []
    n, i, prev_end = len(turns), 0, 0
    while i < n:
        j, size = i, 0
        while j < n:
            ln = len(render_turn(turns[j])) + 1
            if j > i and size + ln > max_chars:
                break
            size += ln
            j += 1
        chunks.append(Chunk(len(chunks), turns[i:j], core_start=prev_end))
        prev_end = j
        if j >= n:
            break
        i = max(j - overlap, i + 1)
    return chunks


def split_chunk(chunk: Chunk, overlap: int = 4) -> tuple[Chunk, Chunk]:
    mid = len(chunk.turns) // 2
    left = Chunk(chunk.index, chunk.turns[:mid], chunk.core_start)
    right = Chunk(chunk.index, chunk.turns[max(0, mid - overlap) :], chunk.turns[mid].idx)
    return left, right
