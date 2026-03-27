---
description: Start the local development environment using UV
---
// turbo-all

# Local Development (Native .venv + UV)

All commands run from the project root: `c:\Users\Yanni\Github\Projects\azure_hello_world`

## Prerequisites
- Python 3.10+ installed
- UV installed (`pip install uv` or via standalone installer)
- `.venv` already exists (created by `uv venv`)

## Steps

1. Sync dependencies from the lockfile:
```powershell
uv sync --frozen
```

2. Run the Streamlit UI (port 8501):
```powershell
uv run streamlit run src/ui/app.py --server.port 8501
```

3. In a second terminal, start the Azure Functions host (port 7071):
```powershell
cd src; $env:PYTHONPATH=".."; uv run func start --port 7071
```

4. Open the Streamlit UI in the browser at `http://localhost:8501`

5. Run tests:
```powershell
uv run pytest tests/ -v
```
