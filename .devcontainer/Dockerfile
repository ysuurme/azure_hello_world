FROM mcr.microsoft.com/devcontainers/python:3.10-bookworm

# 1. Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# 2. Install Azure Functions Core Tools
# We use the Debian repository (matching the base image) rather than Ubuntu to avoid glibc conflicts.
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends gnupg lsb-release curl ca-certificates \
    && curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > /usr/share/keyrings/microsoft-archive-keyring.gpg \
    && echo "deb [arch=amd64,arm64,armhf signed-by=/usr/share/keyrings/microsoft-archive-keyring.gpg] https://packages.microsoft.com/debian/$(lsb_release -rs | cut -d'.' -f1)/prod $(lsb_release -cs) main" > /etc/apt/sources.list.d/dotnetdev.list \
    && apt-get update \
    && apt-get -y install --no-install-recommends azure-functions-core-tools-4 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# 3. (Optional) Pre-install dependencies
WORKDIR /workspaces/azure_hello_world
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen
