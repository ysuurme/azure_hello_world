import base64
import os
import sys

# Ensure the project root is always in path to resolve 'src.' module imports natively
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import streamlit as st

import src.utils.m_ai_client as m_ai_client
from src.agents.workflow_dispatcher import WorkflowDispatcher
from src.utils.m_log import f_log, setup_logging

setup_logging()


def _handle_dispatch(query: str, cm: m_ai_client.ClientManager) -> None:
    dispatcher = WorkflowDispatcher(client_manager=cm)
    result = dispatcher.dispatch(query, st.session_state.maf_state)

    svg_b64 = None
    if "svg" in result.artifacts:
        svg_b64 = base64.b64encode(result.artifacts["svg"]).decode("utf-8")

    st.session_state.maf_state = result.updated_state
    msg_type = "architecture" if svg_b64 else "text"
    ai_msg = {
        "role": "assistant",
        "type": msg_type,
        "content": result.response_text,
        "svg": svg_b64,
        "d2_syntax": result.artifacts.get("d2"),
    }
    st.session_state.chat_history.append(ai_msg)

    with st.chat_message("assistant"):
        st.markdown(result.response_text)
        if svg_b64:
            st.image(base64.b64decode(svg_b64))


st.set_page_config(page_title="Azure Architecture Agent", layout="wide")
st.title("Architecture Agent 🛡️")
st.markdown("### Technical Design Authority Agent")

WELCOME_MESSAGE = (
    "Welcome. Type /help for available commands, or /design <requirements> to design an architecture,"
    " or /diagram <description> to refine a diagram."
)

# Session state initialization
if "maf_state" not in st.session_state:
    st.session_state.maf_state = {}
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [{"role": "assistant", "type": "text", "content": WELCOME_MESSAGE}]

with st.sidebar:
    st.header("Configuration")
    st.info("Running Lean MVP locally. All input routed via WorkflowDispatcher.")
    if st.button("Reset Session"):
        st.session_state.maf_state = {}
        st.session_state.chat_history = [{"role": "assistant", "type": "text", "content": WELCOME_MESSAGE}]
        st.rerun()

# Display chat history
for idx, msg in enumerate(st.session_state.chat_history):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["type"] == "architecture":
            if msg.get("svg"):
                st.image(base64.b64decode(msg["svg"]))
            elif msg.get("d2_syntax"):
                st.error("D2 Compilation Failed. The raw syntax is preserved in the markdown above.")

# Main chat interface
query = st.chat_input("Describe your architecture or answer the clarifying questions...")

if query:
    st.session_state.chat_history.append({"role": "user", "type": "text", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

    with st.spinner("Agent is reasoning..."):
        try:
            f_log("User initiated Analysis from Streamlit.", level="start")
            cm = m_ai_client.ClientManager()

            _handle_dispatch(query, cm)

        except Exception as e:
            f_log(f"Execution Error: {e}", level="error")
            st.error(f"Execution Error: {e}")
