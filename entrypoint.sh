#!/bin/bash

# Start Streamlit in the background
# We bind to 0.0.0.0 to ensure it's accessible outside the container
streamlit run frontend/app.py --server.port 8501 --server.address 0.0.0.0 &

# Start the Azure Functions Host (Foreground Process)
/azure-functions-host/Microsoft.Azure.WebJobs.Script.WebHost