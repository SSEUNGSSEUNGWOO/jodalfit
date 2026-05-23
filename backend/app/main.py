from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.recommendations import router as recommendations_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title="jodalfit API", version="0.0.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(recommendations_router)
