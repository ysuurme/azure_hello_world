# Stage 1: Builder
FROM python:3.10-slim-bookworm AS builder
ENV PYTHONDONTWRITEBYTECODE=1

# Install OS dependencies securely (only in builder stage)
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends \
       gnupg lsb-release curl ca-certificates apt-transport-https \
    && curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > /usr/share/keyrings/microsoft-archive-keyring.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft-archive-keyring.gpg] https://packages.microsoft.com/debian/$(lsb_release -rs | cut -d'.' -f1)/prod $(lsb_release -cs) main" > /etc/apt/sources.list.d/dotnetdev.list \
    && apt-get update && apt-get -y install --no-install-recommends azure-functions-core-tools-4 libicu72 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*
    
# Install D2 securely
RUN curl -fsSL https://d2lang.com/install.sh | sh -s --

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Stage 2: Runtime Environment (Blast Radius Minimization)
FROM builder AS runtime

# Rootless Operation
RUN useradd -m appuser
USER appuser

ENV PYTHONPATH="/app"
WORKDIR /app

# The venv from builder
ENV PATH="/app/.venv/bin:$PATH"

# Copy D2 binary from builder
COPY --from=builder /usr/local/bin/d2 /usr/local/bin/d2

COPY src/ ./src/
COPY entrypoint.sh ./entrypoint.sh

# Azure Functions (7071) and Streamlit (8501)
EXPOSE 7071 8501

# Standard Library Healthcheck
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')" || exit 1

ENTRYPOINT ["./entrypoint.sh"]
