import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from app.pipeline import PipelineError, answer_question
from app.session import Session

st.set_page_config(page_title="Chat with SQL")
st.title("Chat with Chinook DB")

if "session" not in st.session_state:
    st.session_state.session = Session()
if "messages" not in st.session_state:
    st.session_state.messages = []  # [{role, content, sql?}]

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if msg.get("sql"):
            with st.expander("Show generated SQL"):
                st.code(msg["sql"], language="sql")

question = st.chat_input("Ask a question about the Chinook database")
if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.write(question)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            t0 = time.time()
            try:
                answer, sql, _ = answer_question(question, st.session_state.session)
            except PipelineError as e:
                answer, sql = str(e), e.sql
        elapsed = time.time() - t0
        st.write(answer)
        st.caption(f"{elapsed:.1f}s")
        if sql:
            with st.expander("Show generated SQL"):
                st.code(sql, language="sql")

    st.session_state.messages.append(
        {"role": "assistant", "content": answer, "sql": sql}
    )
