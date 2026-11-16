from copilot.llm.base import Completion


class FakeProvider:
    """responses: str | (str, finish_reason) | Exception, consumed in order."""

    def __init__(self, name: str, responses: list):
        self.name, self.model = name, "fake"
        self.responses = list(responses)
        self.calls: list[list[dict]] = []

    def complete(self, messages, **kw):
        self.calls.append(messages)
        r = self.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        text, finish = r if isinstance(r, tuple) else (r, "stop")
        return Completion(
            text=text, provider=self.name, model=self.model, latency_s=0.0, finish_reason=finish
        )


class ConstProvider:
    """Always returns the same text. Used where call counts don't matter."""

    def __init__(self, name: str, text: str):
        self.name, self.model, self.text, self.n = name, "fake", text, 0

    def complete(self, messages, **kw):
        self.n += 1
        return Completion(
            text=self.text,
            provider=self.name,
            model=self.model,
            latency_s=0.0,
            finish_reason="stop",
        )
