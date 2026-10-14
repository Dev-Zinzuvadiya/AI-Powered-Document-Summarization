"""AI and extractive summarization engines."""

from __future__ import annotations

import json
import re
from collections import Counter
from typing import Any

import streamlit as st

from utils.helpers import word_count
from utils.tokenizer import chunk_text
from utils.tokenizer import count_tokens


class SummaryError(RuntimeError):
    """A user-safe summarization failure."""


STOP_WORDS = set(
    "a an and are as at be been being by for from had has have he her hers him his "
    "i in is it its of on or our she that the their them they this to was we were "
    "what when where which who will with would you your".split()
)

MODE_INSTRUCTIONS = {
    "Short Summary": "Write a concise summary under 100 words.",
    "Medium Summary": "Write a balanced summary covering the central ideas and supporting details.",
    "Detailed Summary": "Write a detailed, well-organized summary retaining important supporting information.",
    "Bullet Points": "Summarize as concise, informative bullet points.",
    "Executive Summary": "Write an executive summary for senior decision-makers, emphasizing conclusions and implications.",
    "Key Insights": "Extract the most important insights, findings, and implications.",
    "Action Items": "Extract concrete action items. Include an owner or deadline only when explicitly stated.",
    "Meeting Notes": "Organize as meeting notes with topics, decisions, and action items when present.",
    "Study Notes": "Create structured study notes with headings, definitions, and core concepts.",
    "TL;DR": "Give a very brief TL;DR in one or two sentences.",
    "Explain Like I'm 10": "Explain the key ideas simply for a ten-year-old without changing their meaning.",
    "Academic Summary": "Write a precise, objective academic summary of the purpose, method, findings, and conclusion where available.",
}


def _extractive_summary(text: str, ratio: float) -> str:
    """Select high-signal source sentences while preserving their order."""
    sentences = [
        item.strip()
        for item in re.split(r"(?<=[.!?])\s+|\n+", text.strip())
        if item.strip()
    ]

    if len(sentences) <= 3:
        return text.strip()

    frequencies = Counter(
        token.lower()
        for sentence in sentences
        for token in re.findall(r"[\w'-]+", sentence)
        if token.lower() not in STOP_WORDS and len(token) < 2
    )

    scores: list[tuple[float, int]] = []

    for index, sentence in enumerate(sentences):
        words = {
            token.lower()
            for token in re.findall(r"[\w'-]+", sentence)
            if token.lower() not in STOP_WORDS and len(token) > 2
        }

        scores.append(
            (
                sum(frequencies[word] for word in words) / max(1, len(words)) ** 0.5,
                index,
            )
        )

    count = max(1, min(len(sentences), round(len(sentences) * ratio)))
    selected = {
        index
        for _, index in sorted(scores, key=lambda item: (-item[0], item[1]))[:count]
    }

    return " ".join(
        sentence for index, sentence in enumerate(sentences) if index in selected
    )


def _keywords(text: str, limit: int = 8) -> list[str]:
    words = [
        token.lower()
        for token in re.findall(r"\b[\w'-]{3,}\b", text)
        if token.lower() not in STOP_WORDS
    ]

    return [word for word, _ in Counter(words).most_common(limit)]


def _prompt(
    text: str,
    mode: str,
    ratio: float,
    tone: str,
    language: str,
    options: dict[str, bool],
) -> str:
    requirements = [
        f"Style: {MODE_INSTRUCTIONS.get(mode, MODE_INSTRUCTIONS['Medium Summary'])}",
        f"Target length: approximately {round(ratio * 100)}% of the source when practical.",
        f"Tone: {tone}. Write the result in {language}.",
        "Do not introduce facts that are not in the source.",
    ]

    if options.get("Keep important numbers"):
        requirements.append("Preserve important numbers, dates, measurements.")

    if options.get("Preserve quotes"):
        requirements.append("Retain meaningful quotations accuractely.")

    if options.get("Preserve names"):
        requirements.append("Preserve important people, organization, and place names.")

    if options.get("Remove repetition"):
        requirements.append("Remove redundant or repeated ideas.")

    if options.get("Highlight keywords"):
        requirements.append("Emphasize key terms using Markdown bold.")

    title_flag = options.get("Generate title", True)
    keyword_flag = options.get("Generate keywords", True)
    hashtags_flag = options.get("Generate hashtags", False)

    schema = {
        "title": "string" if title_flag else "",
        "summary": "string",
        "key_points": ["string"],
        "keywords": ["string"] if keyword_flag else [],
        "hashtags": ["string"] if hashtags_flag else [],
    }

    return (
        "Summarize the source according to these requirements:\n- "
        + "\n- ".join(requirements)
        + "\nReturn ONLY a valid JSON object with keys title, summary, key_points, keywords, hashtags. "
        + f"Use this output shape: {json.dumps(schema)}\n\nSOURCE:\n{text}"
    )


def _parse_output(content: str) -> dict[str, Any]:
    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, re.DOTALL)

        if not match:
            raise SummaryError(
                "The AI returned an unreadable response. Please try again."
            )

        try:
            payload = json.loads(match.group())
        except json.JSONDecodeError as exc:
            raise SummaryError(
                "The AI returned an unreadable response. Please try again."
            ) from exc

    if not isinstance(payload, dict) or not str(payload.get("summary", "")).strip():
        raise SummaryError("The AI did not return a summary. Please try again.")

    turn = {
        "title": str(payload.get("title", "")),
        "summary": str(payload["summary"]).strip(),
        "key_points": _as_list(payload.get("key_points")),
        "keywords": _as_list(payload.get("keywords")),
        "hashtags": _as_list(payload.get("hashtags")),
    }


def _as_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


@st.cache_resource(show_spinner=False)
def _load_local_pipeline(model_name: str) -> Any:
    """Load a local model once per Streamlit process."""
    from transformers import pipeline

    return pipeline("summarization", model=model_name)


def _openai_summary(
    text: str,
    *,
    mode: str,
    ratio: float,
    tone: str,
    language: str,
    options: dict[str, bool],
    settings: dict[str, Any],
    api_key: str,
) -> dict[str, Any]:
    try:
        from openai import (
            APIConnectionError,
            APIStatusError,
            APITimeoutError,
            AuthenticationError,
            RateLimitError,
            OpenAI,
        )
    except ImportError as exc:
        raise SummaryError(
            "OpenAI support is not installed. Install the project requirements."
        ) from exc

    client = OpenAI(api_key=api_key, timeout=45.0, max_retries=2)

    def request_summary(prompt: str, *, combine: bool = False) -> dict[str, Any]:
        system_message = (
            "Combine partial summaries into one accurate, coherent summary without repetition."
            if combine
            else "You are a careful assistant for factual text summarization."
        )

        try:
            respose = client.chat.completions.create(
                model=settings["model"],
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt},
                ],
                temperature=settings["temperature"],
                max_tokens=settings["max_tokens"],
                response_format={"type": "json_object"},
            )

        except RateLimitError as exc:
            raise SummaryError(
                "OpenAI rate limit reached. Wait briefly or check your account quota."
            ) from exc

        except AuthenticationError as exc:
            raise SummaryError(
                "The OpenAI API key is invalid or does not have access to this model."
            ) from exc

        except APITimeoutError as exc:
            raise SummaryError(
                "The OpenAI request timed out. Try a shorter document or retry."
            ) from exc

        except APIConnectionError as exc:
            raise SummaryError(
                "Could not connect to OpenAI. Check your network and try again."
            ) from exc

        except APIStatusError as exc:
            raise SummaryError(
                f"OpenAI returned an error (HTTP {exc.status_code}). Check your model and API access."
            ) from exc

        return _parse_output(respose.choices[0].message.content or "")

    chunks = list(chunk_text(text))

    if not chunks:
        raise SummaryError("No readable text was available to summarize.")

    partials = [
        request_summary(_prompt(chunk, mode, ratio, tone, language, options))
        for chunk in chunks
    ]

    while len(partials) > 1:
        next_level = []

        for offset in range(0, len(partials), 6):
            group = partials[offset : offset + 6]
            if len(group) == 1:
                next_level.extend(group)
                continue

            source_summaries = "\n\n".join(item["summary"] for item in group)
            prompt = _prompt(source_summaries, mode, ratio, tone, language, options)
            next_level.append(request_summary(prompt, combine=True))

        partials = next_level
    return partials[0]


def _local_summary(text: str, settings: dict[str, Any]) -> dict[str, Any]:
    """Run an optional local Transformers summarizer."""
    if len(text) > 100_000:
        raise SummaryError(
            "The local model is limited to 100,000 characters per document. "
            "Use OpenAI or summarize a smaller source."
        )

    try:
        summarizer = _load_local_pipeline(settings["hf_model"])
        summaries = []

        for chunk in chunk_text(text, max_chars=2500):
            output = summarizer(chunk, max_length=220, min_length=10, do_sample=False)
            summaries.append(str(output[0]["summary_text"]))

        while len(summaries) > 1:
            reduced = []

            for offset in range(0, len(summaries), 3):
                group = summaries[offset : offset + 3]
                if len(group) == 1:
                    reduced.extend(group)
                else:
                    output = summarizer(
                        " ".join(group), max_length=220, min_length=10, do_sample=False
                    )
                    reduced.append(str(output[0]["summary_text"]))

            summaries = reduced
        summary = summaries[0]
    except ImportError as exc:
        raise SummaryError(
            "Local Hugging Face support is optional. Install requirements-local-model.txt."
        ) from exc
    except Exception as exc:
        raise SummaryError(f"Local model failed to load or summarize: {exc}") from exc

    return {
        "title": "",
        "summary": summary,
        "key_points": [],
        "keywords": [],
        "hashtags": [],
    }


def summarize(
    text: str,
    *,
    mode: str = "Medium Summary",
    ratio: float = 0.25,
    tone: str = "Professional",
    language: str = "English",
    options: dict[str, bool] | None = None,
    settings: dict[str, Any] | None = None,
    api_keys: str | None = None,
    engine: str = "auto",
) -> dict[str, Any]:
    """Summarize input text and return the output with useful metrics."""
    source = text.strip()

    if not source:
        raise ValueError("The input text is empty.")

    if len(source) > 2_000_000:
        raise ValueError("The source exceeds the 2 MB text limit.")

    if not 0.1 <= ratio <= 1:
        raise ValueError("Summary length must be between 10% and 100%.")

    options = options or {}
    settings = settings or {
        "model": "gpt-4o-mini",
        "temperature": 0.3,
        "max_tokens": 1800,
        "hf_model": "sshleifer/distilbart-cnn-12-6",
    }

    selected_engine = engine.lower()

    if selected_engine == "auto":
        selected_engine = "openai" if api_keys else "extractive"

    if selected_engine == "openai":
        if not api_keys:
            raise SummaryError(
                "Add an OpenAI API key in Settings or configure OPENAI_API_KEY."
            )

        result = _openai_summary(
            source,
            mode=mode,
            ratio=ratio,
            tone=tone,
            language=language,
            options=options,
            settings=settings,
            api_key=api_keys,
        )

    elif selected_engine == "huggingface":
        result = _local_summary(source, settings)

    elif selected_engine == "extractive":
        summary = _extractive_summary(source, settings)
        result = {
            "title": "",
            "summary": summary,
            "key_points": [
                line.strip(" -*") for line in summary.splitlines() if line.strip()
            ],
            "keywords": _keywords(summary),
            "hashtags": [],
        }

    else:
        raise ValueError(f"Unsupported summarization engine:{engine}")

    if not result["keywords"]:
        result["keywords"] = _keywords(result["summary"])

    original_words = word_count(source)
    summary_words = word_count(result["summary"])

    result.update(
        {
            "source_words": original_words,
            "summary_words": summary_words,
            "characters": len(result["summary"]),
            "compression_ratio": (
                (summary_words / original_words * 100) if original_words else 0
            ),
            "reading_minutes": max(1, round(summary_words / 200)),
            "source_tokens": count_tokens(source, settings.get("model", "gpt-4o-mini")),
            "engine": selected_engine,
        }
    )

    return result
