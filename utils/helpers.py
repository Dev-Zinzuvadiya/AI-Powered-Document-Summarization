"""Shared constants, settings, history, and presentation helpers."""

from __future__ import annotations

import json
import os
import re
import uuid

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
HISTORY_FILE = ROOT / "data" / "history.json"
MAX_HISTORY_ITEMS = 100

MODES = [
    "Short Summary",
    "Medium Summary",
    "Detailed Summary",
    "Bullet Points",
    "Executive Summary",
    "Key Insights",
    "Action Items",
    "Meeting Notes",
    "Study Notes",
    "TL;DR",
    "Explain Like I'm 10",
    "Academic Summary",
]

TONES = [
    "Professional",
    "Casual",
    "Technical",
    "Business",
    "Academic",
    "Simple",
    "Creative",
]

LANGUAGES = [
    "English",
    "Hindi",
    "Gujarati",
    "Spanish",
    "French",
    "German",
    "Chinese",
    "Japanese",
    "Arabic",
]


def word_count(text: str) -> int:
    """Count Unicode word-like tokens in text."""
    return len(re.findall(r"\b[\w'-]+\b", text, flags=re.UNICODE))


def get_api_key() -> str | None:
    """Read the key from session input, Streamlit secrets, or the environment."""
    session_key = st.session_state.get("openai_api_key_input")

    if session_key:
        return str(session_key).strip()

    try:
        secret_key = st.secrets.get("OPENAI_API_KEY")
    except (FileNotFoundError, AttributeError):
        secret_key = None

    return str(secret_key or os.getenv("OPENAI_API_KEY") or "").strip() or None


def get_summary_settings() -> dict[str, Any]:
    """Return settings with safe defaults."""
    return {
        "model": st.session_state.get("openai_model", "gpt-4o-mini"),
        "temperature": float(st.session_state.get("temperature", 0.3)),
        "max_tokens": int(st.session_state.get("max_tokens", 1800)),
        "hf_model": st.session_state.get("hf_model", "sshleifer/distilbart-cnn-12-6"),
    }


def get_options() -> dict[str, bool]:
    """Read presentation options from Streamlit state."""
    return {
        key: bool(st.session_state.get(key, default))
        for key, default in {
            "Keep important numbers": True,
            "Preserve quotes": False,
            "Preserve names": False,
            "Remove repetition": True,
            "Highlight keywords": False,
            "Generate title": True,
            "Generate keywords": True,
            "Generate hashtags": False,
        }.items()
    }


def apply_theme() -> None:
    """Apply lightweight global styles and optional dark appearance."""
    if st.session_state.get("dark_mode", False):
        st.markdown(
            "<style>"
            ".stApp {background: #101827; color:#f5f5f5;}"
            "[data-testid='stSidebar] {background: #172235}"
            "</style>",
            unsafe_allow_html=True,
        )

    st.markdown(
        """
        <style>
            .block-container {
                width: 100%;
                max-width: 1200px;
                padding-top: 2rem;
                padding-left: 2rem;
                padding-right: 2rem;
                margin: 0 auto;
            }

            h1 {
                letter-spacing: -.04em;
                writing-mode: horizontal-tb;
            }

            .stButton > button {
                border-radius: 10px;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _read_history() -> list[dict[str, Any]]:
    if not HISTORY_FILE.exists():
        return []

    try:
        payload = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Could not read summary history: {exc}") from exc

    if not isinstance(payload, list):
        raise RuntimeError("Summary history has an invalid format.")

    return [entry for entry in payload if isinstance(entry, dict)]


def _write_history(items: list[dict[str, Any]]) -> None:
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = HISTORY_FILE.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    temporary.replace(HISTORY_FILE)


def add_history_entry(result: dict[str, Any]) -> None:
    """Persist only generated output and non-sensitive source metadata."""
    entry = dict(result)
    entry["id"] = uuid.uuid4().hex
    entry["created_at"] = (
        datetime.now(timezone.utc).astimezone().isoformat(timespec="minutes")
    )
    entry.pop("source_text", None)

    items = [entry, *_read_history()]
    _write_history(items[:MAX_HISTORY_ITEMS])


def get_history() -> list[dict[str, Any]]:
    """Return saved summaries, newest first."""
    return _read_history()


def delete_history_entry(entry_id: str) -> None:
    """Remove an entry by its generated identifier."""
    _write_history([item for item in _read_history() if item.get("id") != entry_id])


def format_summary_text(result: dict[str, Any]) -> str:
    """Format a plain-text export."""
    parts = []

    if result.get("title"):
        parts.append(str(result["title"]))
    parts.append(str(result.get("summary", "")))

    if result.get("key_points"):
        parts.extend(
            ["", "Key points:", *[f"- {point}" for point in result["key_points"]]]
        )

    if result.get("keywords"):
        parts.extend(["", "Keywords: " + ", ".join(result["keywords"])])

    return "\n".join(parts).strip()


def save_uploaded_text(upload: Any, limit_bytes: int = 20 * 1024 * 1024) -> bytes:
    """Read a Streamlit upload only if it is within the configured size limit."""
    if upload.size > limit_bytes:
        raise ValueError("The uploaded file exceeds the 20 MB size limit.")

    return upload.getvalue()
