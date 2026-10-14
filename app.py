"""Streamlit entry point and navigation for the AI Text Summarizer."""

import streamlit as st

st.set_page_config(
    page_title="AI Text Summarizer",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded",
)

navigation = st.navigation(
    {
        "Summarize": [
            st.Page("pages/Home.py", title="Home", icon="📝", default=True),
            st.Page("pages/Batch_Summarizer.py", title="Batch Summarizer", icon="📚"),
        ],
        "Library": [
            st.Page("pages/History.py", title="History", icon="🕘"),
            st.Page("pages/Settings.py", title="Settings", icon="⚙️"),
        ],
    }
)

navigation.run()
