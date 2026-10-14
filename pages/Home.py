"""Main summarization page."""

from __future__ import annotations

import json
from typing import Any

import requests
import streamlit as st
import streamlit.components.v1 as components

from utils.doc_reader import read_docx
from utils.export import create_docx, create_pdf, to_markdown
from utils.helpers import (
    add_history_entry,
    apply_theme,
    format_summary_text,
    get_api_key,
    get_summary_settings,
    LANGUAGES,
    MODES,
    TONES,
)

from utils.pdf_reader import read_pdf
from utils.summarizer import SummaryError, summarize
from utils.web_scraper import fetch_webpage
from utils.youtube_loader import fetch_transcript


def _extract_source() -> tuple[str, str]:
    source_type = st.session_state.get("source_type", "Paste text")

    if source_type == "Paste text":
        return st.session_state.get("input_text", "").strip(), "Pasted text"

    if source_type == "Upload PDF":
        upload = st.session_state.get("pdf_upload")
        return (read_pdf(upload), upload.name) if upload else ("", "")

    if source_type == "Upload DOCX":
        upload = st.session_state.get("docx_upload")
        return (read_docx(upload), upload.name) if upload else ("", "")

    if source_type == "YouTube":
        url = st.session_state.get("youtube_url", "").strip()
        return (fetch_transcript(url), url) if url else ("", "")

    return "", ""


def _result_block(result: dict[str, Any]) -> None:
    st.subheader(result.get("title") or "Your summary")
    st.markdown(result["summary"])

    left, middle, right, extra = st.columns(4)
    left.metric("Source words", f"{result['source_words']:,}")
    middle.metric("Summary words", f"{result['summary_words']:,}")
    right.metric("Compression", f"{result['compression_ratio']:.1f}%")
    extra.metric("Approx. source tokens", f"{result['source_tokens']:,}")

    st.caption(
        f'{result["characters"]:,} characters · '
        f'{result["reading_minutes"]} min reading time · '
        f'Generated with {result["engine"]}'
    )

    if result.get("key_points"):
        with st.expander("Key points", expanded=True):
            for point in result["key_points"]:
                st.markdown(f"- {point}")

    if result.get("keywords"):
        st.markdown("**Keywords:**" + " · ".join(result["keywords"]))

    if result.get("hashtags"):
        st.markdown(" ".join(f"#{tag.lstrip('#')}" for tag in result["hashtags"]))

    summary = format_summary_text(result)
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.download_button("Download TXT", summary, "summary.txt", "text/plain")

    with col2:
        st.download_button(
            "Download Markdown", to_markdown(result), "summary.md", "text/markdown"
        )

    with col3:
        try:
            st.download_button(
                "Download PDF", create_pdf(result), "summary.pdf", "application/pdf"
            )
        except (ImportError, RuntimeError, ValueError) as exc:
            st.warning(f"PDF export is unavailable: {exc}")

    with col4:
        try:
            st.download_button(
                "Download DOCX",
                create_docx(result),
                "summary.docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        except (ImportError, RuntimeError, ValueError) as exc:
            st.warning(f"DOCX export is unavailable: {exc}")

    with st.expander("Copy summary"):
        safe_summary = json.dumps(summary, ensure_ascii=False).replace("<", "\\u003c")

        components.html(
            f"""
            <textarea id="summary-copy" readonly
                style="width:100%;
                height:150px;
                font:14px/1.5 sans-serif;
                padding:10px">
            </textarea>
            <button id="copy-button" style="padding:8px 14px;cursor:pointer">Copy to clipboard</button>
            <span id="copy-status" role="status" style="margin-left:10px"></span>
            <script>
                const text = {safe_summary};
                const field = document.getElementById("summary-copy");
                field.value = text;
                document.getElementById("copy-button").addEventListener("click", async () => {{
                    const status = document.getElementById("copy-status");
                    try {{
                        await navigator.clipboard.writeText(text);
                    }} catch (_) {{
                        field.focus();
                        field.select();
                        document.execCommand("copy");
                    }}
                    status.textContent = "Copied";
                }});
            </script>
            """,
            height=215,
        )


def render_home() -> None:
    apply_theme()
    st.title("AT Text Summarizer")
    st.caption(
        "Turn documents, articles, and transcripts into clear, useful summaries."
    )

    source_type = st.selectbox(
        "Choose a source",
        ["Paste text", "Upload PDF", "Upload DOCX", "Website URL", "YouTube"],
        key="source_type",
    )

    if source_type == "Paste text":
        st.text_area(
            "Text to summarize",
            height=250,
            placeholder="Paste an article, report, notes, or any text...",
            key="input_text",
        )
    elif source_type == "Upload PDF":
        st.file_uploader("Choose a PDF (up to 20 MB)", type=["pdf"], key="pdf_upload")
    elif source_type == "Upload DOCX":
        st.file_uploader(
            "Choose a Word document (up to 20 MB)", type=["docx"], key="docx_upload"
        )
    elif source_type == "Website URL":
        st.text_input(
            "Website URL", placeholder="https://example.com/article", key="web_url"
        )
    else:
        st.text_input(
            "YouTube video URL",
            placeholder="https://www.youtube.com/watch?v=...",
            key="youtube_url",
        )

    with st.expander("Summary settings", expanded=True):
        first, second, third = st.columns(3)

        mode = first.selectbox("Style", MODES)
        ratio = second.select_slider(
            "Target length",
            options=[10, 25, 40, 60, 80, 100],
            value=25,
            format_func=lambda value: f"{value}%",
        )

        tone = third.selectbox("Tone", TONES)
        language = st.selectbox("Output language", LANGUAGES)
        engine = st.selectbox(
            "Engine",
            ["auto", "openai", "huggingface", "extractive"],
            format_func=lambda value: {
                "auto": "Automatic (OpenAI when configured, otherwise extractive)",
                "openai": "OpenAI",
                "huggingface": "Local Hugging Face model",
                "extractive": "Extractive (offline)",
            }[value],
        )

        if engine == "huggingface":
            st.caption(
                "The selected local model is usually English-onlyl use OpenAI for translated output."
            )

        option_cols = st.columns(4)
        options = {
            "Keep important numbers": option_cols[0].checkbox("Keep numbers", True),
            "Preserve quotes": option_cols[1].checkbox("Preserve quotes"),
            "Preserve names": option_cols[2].checkbox("Preserve names", True),
            "Remove repetition": option_cols[3].checkbox("Remove repetition", True),
        }

        option_cols = st.columns(4)
        options.update(
            {
                "Highlight keywords": option_cols[0].checkbox("Highlight keywords"),
                "Generate title": option_cols[1].checkbox("Generate title", True),
                "Generate keywords": option_cols[2].checkbox("Generate keywords", True),
                "Generate hashtags": option_cols[3].checkbox("Generate hashtags"),
            }
        )

    if st.button("Generate summary", type="primary", use_container_width=True):
        try:
            with st.spinner("Reading your source and preparing the summary..."):
                text, source_name = _extract_source()

                if not text.strip():
                    st.warning(
                        "Add text or choose a source before generating a summary."
                    )
                    return

                result = summarize(
                    text=text,
                    mode=mode,
                    ratio=ratio / 100,
                    tone=tone,
                    language=language,
                    options=options,
                    settings=get_summary_settings(),
                    api_keys=get_api_key(),
                    engine=engine,
                )

                result["source"] = source_name
                result["mode"] = mode
                result["tone"] = tone
                result["language"] = language

                add_history_entry(result)
                st.session_state["latest_summary"] = result
        except (ValueError, SummaryError, requests.RequestException) as exc:
            st.error(str(exc))

    result = st.session_state.get("latest_summary")
    if result:
        st.divider()
        _result_block(result)


render_home()
