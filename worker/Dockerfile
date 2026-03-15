FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV PYTHONPATH=/app
ENV PATH="/opt/venv/bin:${PATH}"

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY worker/pyproject.toml worker/uv.lock /app/worker/
RUN uv sync --project /app/worker --frozen --no-dev

COPY worker /app/worker
COPY backend /app/backend

WORKDIR /app

CMD ["uv", "run", "--project", "/app/worker", "python", "-m", "worker.main"]
