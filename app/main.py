from fastapi import FastAPI

app = FastAPI(title="Async Payment Service")


@app.get("/health")
async def health():
    return {"status": "ok"}
