# Stage 1: Builder
FROM ghcr.io/astral-sh/uv:python3.13-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Install OS dependencies and D2
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends \
       gnupg lsb-release curl ca-certificates apt-transport-https \
    && curl -fsSL https://d2lang.com/install.sh | sh -s -- \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Stage 2: Runtime
FROM python:3.13-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/app" \
    PATH="/app/.venv/bin:$PATH"

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy D2 binary from builder
COPY --from=builder /usr/local/bin/d2 /usr/local/bin/d2

# Rootless operation
RUN useradd -m appuser
USER appuser

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY src/ ./src/
COPY entrypoint.sh ./entrypoint.sh

# Azure Functions (7071) and Streamlit (8501)
EXPOSE 7071 8501

HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')" || exit 1

CMD ["python", "-m", "src.main"]
ENTRYPOINT ["./entrypoint.sh"]
