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
    "Welcome. Type /help for available commands, /design <requirements> to design an architecture,"
    " or /diagram <description> to create a diagram. Manage saved diagrams from the sidebar"
    " (or /diagram list | open <name> | delete <name>)."
)


def _post_dispatch(query: str, session_state: dict) -> dict:
    resp = requests.post(
        f"{BACKEND_URL}/dispatch",
        json={"query": query, "session_state": session_state},
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()


def _get_diagrams() -> list[dict]:
    try:
        resp = requests.get(f"{BACKEND_URL}/diagrams", timeout=30)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        f_log(f"List diagrams failed: {e}", level="error")
        return []


def _delete_diagram(slug: str) -> None:
    try:
        requests.delete(f"{BACKEND_URL}/diagrams/{slug}", timeout=30).raise_for_status()
    except requests.RequestException as e:
        f_log(f"Delete diagram failed: {e}", level="error")
        st.error(f"Delete failed: {e}")


def _process_query(query: str) -> None:
    st.session_state.chat_history.append({"role": "user", "type": "text", "content": query})
    try:
        data = _post_dispatch(query, st.session_state.maf_state)
    except requests.RequestException as e:
        f_log(f"Backend HTTP error: {e}", level="error")
        st.session_state.chat_history.append(
            {"role": "assistant", "type": "text", "content": f"Backend error: {e}", "svg": None, "d2_syntax": None}
        )
        return
    st.session_state.maf_state = data.get("updated_state", {})
    svg_b64 = data.get("artifacts", {}).get("svg")
    st.session_state.chat_history.append(
        {
            "role": "assistant",
            "type": "architecture" if svg_b64 else "text",
            "content": data.get("response_text", ""),
            "svg": svg_b64,
            "d2_syntax": data.get("artifacts", {}).get("d2"),
        }
    )


def _reset_session() -> None:
    st.session_state.maf_state = {}
    st.session_state.chat_history = [{"role": "assistant", "type": "text", "content": WELCOME_MESSAGE}]


st.set_page_config(page_title="Hello Architect", layout="wide")
st.title("Hello Architect")
st.markdown("### Technical Design Authority Agent")

if "maf_state" not in st.session_state:
    st.session_state.maf_state = {}
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [{"role": "assistant", "type": "text", "content": WELCOME_MESSAGE}]

with st.sidebar:
    st.header("Configuration")
    st.info(f"Backend: {BACKEND_URL}")
    if st.button("Reset Session"):
        _reset_session()
        st.rerun()

    st.divider()
    st.header("Diagrams")
    if st.button("↻ Refresh"):
        st.rerun()
    diagrams = _get_diagrams()
    if not diagrams:
        st.caption("No saved diagrams yet.")
    for d in diagrams:
        st.markdown(f"**{d['subject']}**")
        st.caption(f"`{d['slug']}`")
        col_open, col_del = st.columns(2)
        if col_open.button("Open", key=f"open_{d['slug']}"):
            st.session_state.pending_query = f"/diagram open {d['slug']}"
            st.rerun()
        if col_del.button("Delete", key=f"del_{d['slug']}"):
            _delete_diagram(d["slug"])
            st.rerun()

# Process a sidebar-triggered action (e.g. Open) before rendering history.
if st.session_state.get("pending_query"):
    pending = st.session_state.pop("pending_query")
    with st.spinner("Agent is reasoning..."):
        _process_query(pending)

for i, msg in enumerate(st.session_state.chat_history):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("type") == "architecture" and msg.get("svg"):
            svg_bytes = base64.b64decode(msg["svg"])
            # st.image() decodes via PIL, which cannot read SVG; render it as an inline
            # data-URI <img> instead (the browser renders the vector directly).
            st.markdown(
                f'<img src="data:image/svg+xml;base64,{msg["svg"]}" style="max-width:100%; height:auto"/>',
                unsafe_allow_html=True,
            )
            dl_svg, dl_d2 = st.columns(2)
            dl_svg.download_button(
                "⬇ SVG", data=svg_bytes, file_name="diagram.svg", mime="image/svg+xml", key=f"svg_{i}"
            )
            if msg.get("d2_syntax"):
                dl_d2.download_button(
                    "⬇ D2", data=msg["d2_syntax"], file_name="diagram.d2", mime="text/plain", key=f"d2_{i}"
                )
        elif msg.get("type") == "architecture" and msg.get("d2_syntax"):
            st.error("D2 Compilation Failed. The raw syntax is preserved in the markdown above.")

query = st.chat_input("Describe your architecture or answer the clarifying questions...")
if query:
    f_log("User initiated Analysis from Streamlit.", level="start")
    with st.spinner("Agent is reasoning..."):
        _process_query(query)
    st.rerun()
