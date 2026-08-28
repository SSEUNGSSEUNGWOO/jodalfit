import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.requests import Request

from app.api.events import router as events_router
from app.api.recommendations import router as recommendations_router
from app.core.config import get_settings
from app.core.rate_limit import limiter

settings = get_settings()

logger = logging.getLogger("jodalfit")

app = FastAPI(
    title="jodalfit API",
    version="0.0.1",
    docs_url="/docs" if settings.enable_docs else None,
    redoc_url="/redoc" if settings.enable_docs else None,
    openapi_url="/openapi.json" if settings.enable_docs else None,
)

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(RateLimitExceeded)
def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={
            "error": "요청이 너무 많아요. 잠시 후 다시 시도해주세요.",
            "detail": str(exc.detail) if exc.detail else None,
        },
    )


@app.exception_handler(Exception)
def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """미처리 예외를 스택트레이스와 함께 남긴다.

    이게 없으면 Starlette 기본 핸들러가 본문 "Internal Server Error"만 돌려주고
    원인이 어디에도 안 남아, 간헐적 500을 사후 추적할 수 없다.
    """
    logger.exception(
        "unhandled error: %s %s", request.method, request.url.path
    )
    return JSONResponse(
        status_code=500,
        content={"error": "일시적인 오류가 발생했어요. 잠시 후 다시 시도해주세요."},
    )


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
app.include_router(events_router)
