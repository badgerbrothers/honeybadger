FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

WORKDIR /app

COPY services/rag-service/pyproject.toml ./pyproject.toml
RUN pip install --no-cache-dir uv && uv sync

COPY services/rag-service/app/ ./app/
COPY shared/ ./shared/

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
