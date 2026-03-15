FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV PYTHONPATH=/app
ENV PATH="/opt/venv/bin:${PATH}"

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY backend/pyproject.toml backend/uv.lock /app/backend/
RUN uv sync --project /app/backend --frozen --no-dev

COPY backend /app/backend

WORKDIR /app/backend

CMD ["uv", "run", "--project", "/app/backend", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
