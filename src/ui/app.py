import sys
import os
# Ensure the project root is always in path to resolve 'src.' module imports natively
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import streamlit as st
import json
from src.utils.m_api_adapter import fetch_architecture_insight
from src.utils.m_log import f_log, setup_logging

# Initialize standardized telemetry
setup_logging()

st.set_page_config(page_title="Azure Architecture Agent", layout="wide")

st.title("Architecture Agent 🛡️")
st.markdown("### Technical Design Authority Agent")

# Sidebar for configuration
with st.sidebar:
    st.header("Configuration")
    # Unified Container Mode: Streamlit talks to Localhost Port 80 (Azure Function)
    api_url = st.text_input("Agent Endpoint", value="http://localhost:7071/api/agent_trigger")
    st.info("Running in Unified Container Mode.")

# Main chat interface
query = st.text_area("Describe your architecture or ask a question:", height=150, 
                     value="Evaluating the cost impact of moving to a multi-region App Service with Azure Front Door.")

def handle_query(query: str, api_url: str) -> None:
    """Executes the analysis flow using early guard clauses to minimize indentation limits."""
    if not query:
        st.warning("Please enter a query.")
        return

    with st.spinner("Agent is reasoning..."):
        try:
            f_log("User initiated Analysis from Streamlit.", c_type="start")
            data = fetch_architecture_insight(query, api_url)
            
            st.subheader("Recommendation")
            st.write(data.get("recommendation", "No recommendation provided."))
            
            insight = data.get("insight", {})
            if "cost_evaluation" in insight:
                st.subheader("💰 Cost Trade-off Matrix")
                st.json(insight["cost_evaluation"])
            
            with st.expander("Raw Response Debug"):
                st.json(data)
                
        except Exception as e:
            f_log(f"Connection Error: {e}", c_type="error")
            st.error(f"Connection Error: {e}")
            st.caption("Hint: Ensure the Azure Function host is running.")

if st.button("Analyze Architecture", type="primary"):
    handle_query(query, api_url)