import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from copilot.api.routes import router

app = FastAPI(title="Meeting Co-Pilot", version="0.1.0")
app.include_router(router)
log = logging.getLogger("copilot.api")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    log.exception("unhandled error on %s", request.url.path)  # stack trace stays in the server log
    return JSONResponse({"detail": "internal error"}, status_code=500)
