from fastapi import FastAPI

app = FastAPI(title="Mini Payment Gateway", version="0.1.0")


@app.get("/health", tags=["health"])
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
