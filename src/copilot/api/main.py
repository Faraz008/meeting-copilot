from fastapi import FastAPI

app = FastAPI(title="Meeting Co-Pilot")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
