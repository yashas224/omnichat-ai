import base64
import os
from pathlib import Path
from urllib.parse import quote

import requests
import streamlit as st

QA_CHAT = "QA Chat"
DOCUMENT_QA_CHAT = "Document QA Chat"

FLOWS = {QA_CHAT: "qa_chat", DOCUMENT_QA_CHAT: "document_qa_chat"}
MIN_USER_ID_LENGTH = 5
BACKEND_URL = os.getenv("OMNICHAT_BACKEND_URL", "http://localhost:8000")
REQUEST_TIMEOUT_SECONDS = 120
METRICS_TIMEOUT_SECONDS = 5
CHAT_HEIGHT_PIXELS = 600
BACKGROUND_IMAGE = Path(__file__).parent / "assets" / "background.svg"


def ask_backend(flow: str, user_id: str, user_query: str):
    response = requests.post(
        f"{BACKEND_URL}/chat/{flow}/{quote(user_id, safe='')}",
        json={"user_query": user_query},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()["result"]


def get_metrics(user_id: str):
    response = requests.get(f"{BACKEND_URL}/metrics/{quote(user_id, safe='')}", timeout=METRICS_TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.json()


def render_metrics(user_id: str, user_id_valid: bool):
    st.subheader("LLM Metrics")
    if not user_id_valid:
        st.caption("Enter a valid User ID to see metrics.")
        return
    try:
        metrics = get_metrics(user_id)
    except requests.RequestException:
        st.caption("Metrics are unavailable.")
        return
    tokens_column, latency_column = st.columns(2)
    calls_column, errors_column = st.columns(2)
    tokens_column.metric("Total Tokens", f"{metrics['total_tokens']:,}")
    latency_column.metric("Avg Latency", f"{metrics['average_latency']:.2f}s")
    calls_column.metric("Total LLM Calls", f"{metrics['total_llm_calls']:,}")
    errors_column.metric("LLM Errors", f"{metrics['llm_errors']:,}")


def render_background():
    image = base64.b64encode(BACKGROUND_IMAGE.read_bytes()).decode()
    st.html(f"""
    <style>
    [data-testid="stApp"] {{
        background: url("data:image/svg+xml;base64,{image}") center / cover fixed;
    }}
    [data-testid="stHeader"], [data-testid="stBottom"], [data-testid="stBottom"] > div {{
        background: transparent;
    }}
    .st-key-chat_history {{
        background: rgba(11, 16, 38, 0.65);
        backdrop-filter: blur(6px);
    }}
    </style>
    """)


def render_message(message: dict):
    if "content" in message:
        st.markdown(message["content"])
    elif "error" in message:
        st.error(message["error"])
    elif message["result"] is None:
        st.warning("This question could not be processed. Please rephrase it and try again.")
    else:
        st.markdown(message["result"]["description"])
        for point in message["result"]["sub_points"]:
            st.markdown(f"- {point['content']}")
            for source in point["sources"]:
                st.caption(source)


st.set_page_config(page_title="OmniChat AI")
render_background()
st.title("OmniChat AI")

with st.sidebar:
    user_id = st.text_input("User ID", help=f"Minimum {MIN_USER_ID_LENGTH} characters").strip()
    selected_mode = st.selectbox("Chat Mode", options=list(FLOWS))
    metrics_section = st.container()

user_id_valid = len(user_id) >= MIN_USER_ID_LENGTH and "/" not in user_id
if user_id and not user_id_valid:
    st.sidebar.error(f"User ID must be at least {MIN_USER_ID_LENGTH} characters and cannot contain '/'.")
elif not user_id:
    st.info("Enter a User ID in the sidebar to start chatting.")

question = st.chat_input("Ask a question", disabled=not user_id_valid)

# Kept per user so changing the User ID doesn't show another user's conversation
messages = st.session_state.setdefault("messages", {}).setdefault(user_id, [])

if messages or question:
    with st.container(height=CHAT_HEIGHT_PIXELS, autoscroll=True, key="chat_history"):
        for message in messages:
            with st.chat_message(message["role"]):
                render_message(message)

        if question:
            user_message = {"role": "user", "content": question}
            messages.append(user_message)
            with st.chat_message("user"):
                render_message(user_message)

            with st.chat_message("assistant"):
                try:
                    with st.spinner("Thinking..."):
                        reply = {"role": "assistant", "result": ask_backend(FLOWS[selected_mode], user_id, question)}
                except requests.RequestException as error:
                    reply = {"role": "assistant", "error": f"Could not get an answer from the backend: {error}"}
                messages.append(reply)
                render_message(reply)

# Rendered last so the numbers include the question answered in this run
with metrics_section:
    render_metrics(user_id, user_id_valid)
