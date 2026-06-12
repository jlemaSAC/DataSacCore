from fastapi import FastAPI

from app.routers import health

app = FastAPI(title="FastAPI Basic Starter", version="0.1.0")

app.include_router(health.router)


@app.get("/", tags=["root"])
async def root() -> dict[str, str]:
    return {"message": "Hello World"}

