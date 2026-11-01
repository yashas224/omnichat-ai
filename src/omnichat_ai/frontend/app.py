import streamlit as st

QA_CHAT = "QA Chat"
DOCUMENT_QA_CHAT = "Document QA Chat"

st.set_page_config(page_title="OmniChat AI")
st.title("OmniChat AI")

with st.sidebar:
    openai_api_key = st.text_input("OpenAI API Key", type="password")
    selected_modes = st.multiselect(
        "Chat Mode",
        options=[QA_CHAT, DOCUMENT_QA_CHAT],
        default=[QA_CHAT],
    )
