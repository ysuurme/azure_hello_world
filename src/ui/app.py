import sys
import os
import base64

# Ensure the project root is always in path to resolve 'src.' module imports natively
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import streamlit as st
import src.utils.m_ai_client as m_ai_client
from src.utils.m_orchestrator import AgenticOrchestrator
from src.utils.m_diagram_engine import DiagramEngine
from src.utils.m_persist_design import ArchitecturePersister
from src.utils.m_log import f_log, setup_logging

setup_logging()
st.set_page_config(page_title="Azure Architecture Agent", layout="wide")
st.title("Architecture Agent 🛡️")
st.markdown("### Technical Design Authority Agent")

# Session state initialization
if "maf_state" not in st.session_state:
    st.session_state.maf_state = {}
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [{"role": "assistant", "type": "text", "content": "Welcome. Please describe the architecture you want to build."}]
    
with st.sidebar:
    st.header("Configuration")
    st.info("Running Lean MVP locally with direct orchestrator bindings.")
    if st.button("Reset Session"):
        st.session_state.maf_state = {}
        st.session_state.chat_history = [{"role": "assistant", "type": "text", "content": "Welcome. Please describe the architecture you want to build."}]
        st.rerun()

# Display chat history Context
for idx, msg in enumerate(st.session_state.chat_history):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["type"] == "architecture" and msg.get("svg"):
            st.image(base64.b64decode(msg["svg"]))

# Main chat interface for iteration
query = st.chat_input("Describe your architecture or answer the clarifying questions...")

if query:
    st.session_state.chat_history.append({"role": "user", "type": "text", "content": query})
    with st.chat_message("user"):
         st.markdown(query)
         
    with st.spinner("Agent is reasoning..."):
        try:
            f_log("User initiated Analysis from Streamlit.", c_type="start")
            
            # Use Orchestrator Natively with a single shared ClientManager
            # Create the shared ClientManager at app bootstrap (use `az login` locally
            # or set service principal env vars in your .env file).
            cm = m_ai_client.ClientManager()
            orchestrator = AgenticOrchestrator(client_manager=cm)
            updated_state, output_text = orchestrator.orchestrate_cycle(query, st.session_state.maf_state)
            
            svg_b64 = None
            if updated_state.get("phase") == "GENERATION":
                f_log("Architecture Finalized. Triggering Pipelines.", c_type="process")
                visualizer = DiagramEngine()
                
                # Mock MVP generation logic 
                sample_d2 = "direction: right\nUI -> Orchestrator -> AI Search\nAI Search -> Capability Repo"
                svg_bytes = visualizer.generate_svg(sample_d2)
                
                if svg_bytes:
                    svg_b64 = base64.b64encode(svg_bytes).decode('utf-8')
                    
                persister = ArchitecturePersister()
                persister.archive_solution("Lean-MVP-Design", output_text, svg_bytes)
            
            # Update local State Machine tracking parameters
            st.session_state.maf_state = updated_state
            
            # Formulate the AI's response format
            msg_type = "architecture" if updated_state.get("phase") == "GENERATION" else "text"
            
            ai_msg = {
                 "role": "assistant",
                 "type": msg_type,
                 "content": output_text,
                 "svg": svg_b64
            }
            st.session_state.chat_history.append(ai_msg)
            
            with st.chat_message("assistant"):
                 st.markdown(output_text)
                 if svg_b64:
                     st.image(base64.b64decode(svg_b64))
                     
        except Exception as e:
            f_log(f"Execution Error: {e}", c_type="error")
            st.error(f"Execution Error: {e}")