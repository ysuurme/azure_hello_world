---
description: Build and run the Docker container locally via Rancher Desktop
---
// turbo-all

# Docker Container Validation (Rancher Desktop)

All commands run from the project root: `c:\Users\Yanni\Github\Projects\azure_hello_world`

## Prerequisites
- Rancher Desktop running with **dockerd (moby)** engine
- A `.env` file at the project root (copy from `.env.example`)

## Steps

1. Build and start the container with live-reload volume mounts:
```powershell
docker compose -f docker-compose.dev.yml up --build
```

2. Open the Streamlit UI at `http://localhost:8501`

3. Edit any file under `src/` on your host — changes appear in the container automatically.

4. Test the Azure Functions endpoint:
```powershell
Invoke-RestMethod -Uri "http://localhost:7071/api/ArchitectureAdvisorTrigger" -Method POST -ContentType "application/json" -Body '{"query": "Evaluate cost of multi-region App Service with Azure Front Door"}'
```

5. Stop the container:
```powershell
docker compose -f docker-compose.dev.yml down
```
