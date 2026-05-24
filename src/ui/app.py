from __future__ import annotations

import base64
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import requests
import streamlit as st

from src.utils.m_log import f_log, setup_logging

setup_logging()

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")
WELCOME_MESSAGE = (
    "Welcome. Type /help for available commands, or /design <requirements> to design an architecture,"
    " or /diagram <description> to refine a diagram."
)


def _call_backend(query: str, session_state: dict) -> dict:
    resp = requests.post(
        f"{BACKEND_URL}/dispatch",
        json={"query": query, "session_state": session_state},
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()


def _handle_dispatch(query: str) -> None:
    try:
        data = _call_backend(query, st.session_state.maf_state)
    except requests.RequestException as e:
        f_log(f"Backend HTTP error: {e}", level="error")
        st.error(f"Backend error: {e}")
        return

    st.session_state.maf_state = data.get("updated_state", {})
    svg_b64: str | None = data.get("artifacts", {}).get("svg")
    msg_type = "architecture" if svg_b64 else "text"
    ai_msg = {
        "role": "assistant",
        "type": msg_type,
        "content": data.get("response_text", ""),
        "svg": svg_b64,
        "d2_syntax": data.get("artifacts", {}).get("d2"),
    }
    st.session_state.chat_history.append(ai_msg)

    with st.chat_message("assistant"):
        st.markdown(data.get("response_text", ""))
        if svg_b64:
            st.image(base64.b64decode(svg_b64))


st.set_page_config(page_title="Azure Architecture Agent", layout="wide")
st.title("Architecture Agent 🛡️")
st.markdown("### Technical Design Authority Agent")

if "maf_state" not in st.session_state:
    st.session_state.maf_state = {}
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [{"role": "assistant", "type": "text", "content": WELCOME_MESSAGE}]

with st.sidebar:
    st.header("Configuration")
    st.info(f"Backend: {BACKEND_URL}")
    if st.button("Reset Session"):
        st.session_state.maf_state = {}
        st.session_state.chat_history = [{"role": "assistant", "type": "text", "content": WELCOME_MESSAGE}]
        st.rerun()

for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["type"] == "architecture":
            if msg.get("svg"):
                st.image(base64.b64decode(msg["svg"]))
            elif msg.get("d2_syntax"):
                st.error("D2 Compilation Failed. The raw syntax is preserved in the markdown above.")

query = st.chat_input("Describe your architecture or answer the clarifying questions...")

if query:
    st.session_state.chat_history.append({"role": "user", "type": "text", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

    with st.spinner("Agent is reasoning..."):
        f_log("User initiated Analysis from Streamlit.", level="start")
        _handle_dispatch(query)
