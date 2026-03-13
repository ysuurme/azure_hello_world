FROM python:3.10-slim-bookworm

# 1. Install system dependencies for Azure Functions Core Tools
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends \
       gnupg lsb-release curl ca-certificates apt-transport-https \
    && curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > /usr/share/keyrings/microsoft-archive-keyring.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft-archive-keyring.gpg] https://packages.microsoft.com/debian/$(lsb_release -rs | cut -d'.' -f1)/prod $(lsb_release -cs) main" > /etc/apt/sources.list.d/dotnetdev.list \
    && apt-get update \
    && apt-get -y install --no-install-recommends azure-functions-core-tools-4 libicu72 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# 2. Install uv for dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# 3. Set working directory and install Python dependencies
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

# 4. Copy application source
COPY src/ ./src/
COPY entrypoint.sh ./entrypoint.sh
RUN chmod +x ./entrypoint.sh

# Ensure 'src' package imports resolve via PYTHONPATH
ENV PYTHONPATH="/app"
# Prevent __pycache__ conflicts when source is volume-mounted for dev
ENV PYTHONDONTWRITEBYTECODE=1

# 5. Expose ports: Azure Functions (7071) and Streamlit (8501)
EXPOSE 7071 8501

ENTRYPOINT ["./entrypoint.sh"]
