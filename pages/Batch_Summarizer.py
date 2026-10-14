"""Batch PDF summarization and ZIP download."""

from __future__ import annotations

import io
import re
import zipfile

import streamlit as st

from utils.helpers import apply_theme, get_api_key, get_summary_settings
from utils.pdf_reader import read_pdf
from utils.summarizer import SummaryError, summarize

apply_theme()
st.title("Batch PDF Summarizer")
st.caption("Summarize several PDFs and download the results together.")

files = st.file_uploader(
    "Upload PDFs (maximum 20 MB each)", type=["pdf"], accept_multiple_files=True
)

mode = st.selectbox(
    "Summary style",
    ["Short Summary", "Medium Summary", "Bullet Points", "Executive Summary"],
)

language = st.selectbox(
    "Output language",
    [
        "English",
        "Hindi",
        "Gujarati",
        "Spanish",
        "French",
        "German",
        "Chinese",
        "Japanese",
        "Arabic",
    ],
)

if st.button("Summarize PDFs", type="primary", disabled=not files):
    archive = io.BytesIO()
    failed = list[str] = []

    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as output_zip:
        progress = st.progress(0)
        for index, uploaded in enumerate(files):
            try:
                text = read_pdf(uploaded)
                result = summarize(
                    text,
                    mode=mode,
                    ratio=0.25,
                    tone="Professional",
                    language=language,
                    options={"Generate title": True, "Generate keywords": True},
                    settings=get_summary_settings(),
                    api_keys=get_api_key(),
                )

                safe_name = (
                    re.sub(
                        r"[^A-Za-z0-9_-]+",
                        "_",
                        uploaded.name.rsplit(".", 1)[0],
                    ).strip("_")
                    or "document"
                )
                output_zip.writestr(
                    f"{index + 1:03d}_{safe_name}_summary.md",
                    f"# {result['title']}\n\n{result['summary']}\n",
                )

                st.success(f"Summarized {uploaded.name}")
            except (ValueError, SummaryError) as exc:
                failed.append(f"{uploaded.name}: {exc}")
            progress.progress((index + 1) / len(files))

    archive.seek(0)
    st.download_button(
        "Download summaries ZIP", archive, "summaries.zip", "application/zip"
    )

    for error in failed:
        st.error(error)
