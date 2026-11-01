import base64
import json
import os
from pathlib import Path
from urllib.parse import quote

import requests
import streamlit as st
from langchain_core.utils.json import parse_partial_json

QA_CHAT = "QA Chat"
DOCUMENT_QA_CHAT = "Document QA Chat"

FLOWS = {QA_CHAT: "qa_chat", DOCUMENT_QA_CHAT: "document_qa_chat"}
MIN_USER_ID_LENGTH = 5
BACKEND_URL = os.getenv("OMNICHAT_BACKEND_URL", "http://localhost:8000")
REQUEST_TIMEOUT_SECONDS = 120
METRICS_TIMEOUT_SECONDS = 5
CHAT_HEIGHT_PIXELS = 600
AGENT_PANEL_WIDTH = "24rem"
SIDEBAR_COLOR = "rgb(38, 39, 48)"
BACKGROUND_IMAGE = Path(__file__).parent / "assets" / "background.svg"


def stream_backend(flow: str, user_id: str, user_query: str):
    with requests.post(
        f"{BACKEND_URL}/chat/{flow}/{quote(user_id, safe='')}",
        json={"user_query": user_query},
        timeout=REQUEST_TIMEOUT_SECONDS,
        stream=True,
    ) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if not line.startswith(b"data: "):
                continue
            payload = line.removeprefix(b"data: ")
            if payload == b"[DONE]":
                return
            yield json.loads(payload)


def clear_backend_chat(user_id: str):
    response = requests.delete(f"{BACKEND_URL}/chat/{quote(user_id, safe='')}", timeout=METRICS_TIMEOUT_SECONDS)
    response.raise_for_status()


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
    [data-testid="stMainBlockContainer"] {{
        padding-right: calc({AGENT_PANEL_WIDTH} + 2rem);
    }}
    .st-key-agent_state {{
        position: fixed;
        /* Starts below Streamlit's toolbar so entries never slide under it; the shadow fills the gap */
        top: 3.75rem;
        right: 0;
        bottom: 0;
        width: {AGENT_PANEL_WIDTH};
        height: auto !important;
        padding: 1rem;
        background: {SIDEBAR_COLOR};
        box-shadow: 0 -3.75rem 0 {SIDEBAR_COLOR};
        border: none;
        border-radius: 0;
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


def format_partial_answer(text: str):
    # The agent streams its structured response as JSON, so parse what has arrived so far
    try:
        answer = parse_partial_json(text)
    except ValueError:
        return text
    if not isinstance(answer, dict):
        return text
    points = [f"- {point['content']}" for point in answer.get("sub_points", []) if point.get("content")]
    return "\n".join([answer.get("description", ""), "", *points])


def render_agent_event(event: dict):
    if event["type"] == "question":
        st.caption(f"Question: {event['data']}")
        return
    source = ", ".join(event["data"])
    with st.expander(f"{event['type']} · {source}"):
        st.json(event["data"], expanded=2)


def stream_reply(flow: str, user_id: str, user_query: str, events: list, state_panel):
    answer_placeholder = st.empty()
    answer_placeholder.caption("Thinking...")
    answer_id = None
    answer_text = ""
    result = None
    for event in stream_backend(flow, user_id, user_query):
        if event["type"] == "messages":
            chunk = event["data"][0]
            # Tool calls and tool results also arrive here, but only model text is the answer
            if chunk["type"] != "AIMessageChunk" or not chunk["content"]:
                continue
            if chunk["id"] != answer_id:
                answer_id = chunk["id"]
                answer_text = ""
            answer_text += chunk["content"]
            answer_placeholder.markdown(format_partial_answer(answer_text))
            continue
        events.append(event)
        with state_panel:
            render_agent_event(event)
        # Only the top-level nodes set return_result; a blocked question leaves it as None
        if not event["namespace"]:
            for node_output in event["data"].values():
                result = node_output.get("return_result", result)
    answer_placeholder.empty()
    return result


st.set_page_config(page_title="OmniChat AI", layout="wide")
render_background()
st.title("OmniChat AI")

with st.sidebar:
    user_id = st.text_input("User ID", help=f"Minimum {MIN_USER_ID_LENGTH} characters").strip()
    user_id_valid = len(user_id) >= MIN_USER_ID_LENGTH and "/" not in user_id
    selected_mode = st.selectbox("Chat Mode", options=list(FLOWS))
    clear_screen_clicked = st.button(
        "Clear Chat Screen",
        disabled=not user_id_valid,
        width="stretch",
        help="Clears this screen only. The agent still remembers the conversation.",
    )
    # Not tied to the visible messages: after a page refresh they are gone but the agent still remembers them
    clear_history_clicked = st.button(
        "Clear Chat History",
        disabled=not user_id_valid,
        width="stretch",
        help="Clears this screen and makes the agent forget the conversation.",
    )
    metrics_section = st.container()

if user_id and not user_id_valid:
    st.sidebar.error(f"User ID must be at least {MIN_USER_ID_LENGTH} characters and cannot contain '/'.")

if not user_id:
    st.info("Enter a User ID in the sidebar to start chatting.")

chat_history = st.container(height=CHAT_HEIGHT_PIXELS, autoscroll=True, key="chat_history")
# Inside the main area instead of pinned to the page, so it stays as wide as the messages above it
with st.container():
    question = st.chat_input("Ask a question", disabled=not user_id_valid)

# Kept per user so changing the User ID doesn't show another user's conversation
messages = st.session_state.setdefault("messages", {}).setdefault(user_id, [])
# Holds every question's events in order, oldest first, with a marker where each question starts
agent_events = st.session_state.setdefault("agent_events", {}).setdefault(user_id, [])
if clear_history_clicked:
    try:
        clear_backend_chat(user_id)
        clear_screen_clicked = True
    except requests.RequestException as error:
        st.sidebar.error(f"Could not clear the chat history: {error}")
if clear_screen_clicked:
    messages.clear()
    agent_events.clear()
if question:
    agent_events.append({"type": "question", "data": question})

state_panel = st.container(height=CHAT_HEIGHT_PIXELS, autoscroll=True, key="agent_state")
with state_panel:
    for agent_event in agent_events:
        render_agent_event(agent_event)

with chat_history:
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
                result = stream_reply(FLOWS[selected_mode], user_id, question, agent_events, state_panel)
                reply = {"role": "assistant", "result": result}
            except requests.RequestException as error:
                reply = {"role": "assistant", "error": f"Could not get an answer from the backend: {error}"}
            messages.append(reply)
            render_message(reply)

# Rendered last so the numbers include the question answered in this run
with metrics_section:
    render_metrics(user_id, user_id_valid)
