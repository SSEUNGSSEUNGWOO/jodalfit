import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.requests import Request

from app.api.events import router as events_router
from app.api.feedback import router as feedback_router
from app.api.qualifications import router as qualifications_router
from app.api.recommendations import router as recommendations_router
from app.core.config import get_settings
from app.core.rate_limit import limiter

settings = get_settings()

if settings.sentry_dsn:
    import sentry_sdk

    # FastAPI 통합은 자동 감지. 미처리 예외 + 로거의 error 이상을 보낸다. 트레이싱은 끔(무료 한도).
    # max_request_body_size="never": 기본값(medium)은 예외 때 요청 본문을 같이 보낸다 — /feedback 본문·이메일이 Sentry 로 새는 걸 막는다.
    sentry_sdk.init(dsn=settings.sentry_dsn, traces_sample_rate=0, send_default_pii=False, max_request_body_size="never")

logger = logging.getLogger("jodalfit")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """kure 공간이면 ONNX 세션(없으면 모델 다운로드)을 백그라운드에서 미리 띄운다.

    첫 요청이 409MB 다운로드를 기다리면 타임아웃이다. 스레드라 startup 은 막지 않는다.
    Railway 는 재시작마다 다시 받는다 — KURE_MODEL_DIR 을 볼륨으로 잡아야 캐시가 남는다.
    """
    if settings.embed_space == "kure":

        def warm() -> None:
            from app.services import local_embed

            try:
                local_embed.embed_texts_kure(["워밍업"])
                logger.info("KURE 세션 준비 완료")
            except Exception:
                logger.exception("KURE 워밍 실패 — 첫 요청이 모델 로드를 기다린다")

        threading.Thread(target=warm, daemon=True).start()
    yield


app = FastAPI(
    lifespan=lifespan,
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
app.include_router(feedback_router)
app.include_router(qualifications_router)
