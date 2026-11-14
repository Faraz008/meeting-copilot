from copilot.llm.factory import build_router

r = build_router(cache_mode="off")
for p in r.providers:
    c = r.call(p, [{"role": "user", "content": 'Reply with JSON {"pong": true}'}], purpose="ping")
    print(p.name, c.model, f"{c.latency_s:.1f}s", c.text[:60])
