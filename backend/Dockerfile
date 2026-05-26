FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

ENV PYTHONUNBUFFERED=1
CMD ["sh", "-c", "uv run uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
