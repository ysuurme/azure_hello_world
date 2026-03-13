import streamlit as st
import requests
import json

st.set_page_config(page_title="Azure Architecture Agent", layout="wide")

st.title("Azure Architecture Agent 🛡️")
st.markdown("### Technical Design Authority Agent")

# Sidebar for configuration
with st.sidebar:
    st.header("Configuration")
    # Unified Container Mode: Streamlit talks to Localhost Port 80 (Azure Function)
    api_url = st.text_input("Agent Endpoint", value="http://localhost:7071/api/ArchitectureAdvisorTrigger")
    st.info("Running in Unified Container Mode.")

# Main chat interface
query = st.text_area("Describe your architecture or ask a question:", height=150, 
                     value="Evaluating the cost impact of moving to a multi-region App Service with Azure Front Door.")

if st.button("Analyze Architecture", type="primary"):
    if not query:
        st.warning("Please enter a query.")
    else:
        with st.spinner("Agent is reasoning..."):
            try:
                payload = {"query": query}
                response = requests.post(api_url, json=payload, timeout=120)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Display Recommendation
                    st.subheader("Recommendation")
                    st.write(data.get("recommendation", "No recommendation provided."))
                    
                    # Display Insight/Trade-off Matrix
                    insight = data.get("insight", {})
                    if "cost_evaluation" in insight:
                        st.subheader("💰 Cost Trade-off Matrix")
                        cost_data = insight["cost_evaluation"]
                        st.json(cost_data)
                    
                    with st.expander("Raw Response Debug"):
                        st.json(data)
                else:
                    st.error(f"Error {response.status_code}: {response.text}")
            except Exception as e:
                st.error(f"Connection Error: {e}")
                st.caption("Hint: Ensure the Azure Function host is running.")