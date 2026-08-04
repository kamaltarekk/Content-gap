FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

# Install uv for fast, reproducible dependency resolution.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml ./
RUN uv pip install --system -r pyproject.toml

COPY . .
EXPOSE 3001
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "3001"]
