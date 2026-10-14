"""Application settings page."""

import streamlit as st

from utils.helpers import apply_theme


def _reset_settings() -> None:
    """Reset settings before Streamlit instantiates this page's widgets."""
    for key in (
        "openai_api_key_input",
        "openai_model",
        "temperature",
        "max_tokens",
        "hf_model",
        "dark_mode",
    ):
        st.session_state.pop(key, None)
    st.session_state["settings_reset"] = True


apply_theme()
st.title("Settings")
st.caption(
    "API keys remain in the current session unless supplied through Streamlit secrets or environment variables."
)

if st.session_state.pop("settings_reset", False):
    st.success("Session settings reset.")

st.text_input(
    "OpenAI API key",
    type="password",
    key="openai_api_key_input",
    help="Alternatively configure OPENAI_API_KEY as an environment variable or Streamlit secret.",
)

st.selectbox(
    "OpenAI model",
    ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini", "gpt-4.1"],
    key="openai_model",
)

st.slider("Temperature", 0.0, 1.0, 0.3, 0.1, key="temperature")
st.slider("Maximum output tokens", 256, 8000, 1800, 256, key="max_tokens")
st.text_input(
    "Hugging Face model (optional)",
    value="sshleifer/distilbart-cnn-12-6",
    key="hf_model",
)

st.toggle("Dark appearance", key="dark_mode")

st.button("Reset settings", on_click=_reset_settings)
