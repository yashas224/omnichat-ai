import os
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


def ask_backend(flow: str, user_id: str, user_query: str):
    response = requests.post(
        f"{BACKEND_URL}/chat/{flow}/{quote(user_id, safe='')}",
        json={"user_query": user_query},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()["result"]


def get_metrics():
    response = requests.get(f"{BACKEND_URL}/metrics", timeout=METRICS_TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.json()


def render_metrics():
    st.subheader("LLM Metrics")
    try:
        metrics = get_metrics()
    except requests.RequestException:
        st.caption("Metrics are unavailable.")
        return
    tokens_column, latency_column = st.columns(2)
    calls_column, errors_column = st.columns(2)
    tokens_column.metric("Total Tokens", f"{metrics['total_tokens']:,}")
    latency_column.metric("Avg Latency", f"{metrics['average_latency']:.2f}s")
    calls_column.metric("Total LLM Calls", f"{metrics['total_llm_calls']:,}")
    errors_column.metric("LLM Errors", f"{metrics['llm_errors']:,}")


st.set_page_config(page_title="OmniChat AI")
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

if question:
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        try:
            with st.spinner("Thinking..."):
                result = ask_backend(FLOWS[selected_mode], user_id, question)
        except requests.RequestException as error:
            st.error(f"Could not get an answer from the backend: {error}")
        else:
            if result is None:
                st.warning("This question could not be processed. Please rephrase it and try again.")
            else:
                st.markdown(result["description"])
                for point in result["sub_points"]:
                    st.markdown(f"- {point['content']}")
                    for source in point["sources"]:
                        st.caption(source)

# Rendered last so the numbers include the question answered in this run
with metrics_section:
    render_metrics()
