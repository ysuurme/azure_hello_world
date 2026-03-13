#!/bin/bash

# Start Streamlit in the background
# Bind to 0.0.0.0 to ensure accessibility outside the container
uv run streamlit run src/ui/app.py --server.port 8501 --server.address 0.0.0.0 &

# Start the Azure Functions Host in the foreground
cd src && uv run func start --port 7071