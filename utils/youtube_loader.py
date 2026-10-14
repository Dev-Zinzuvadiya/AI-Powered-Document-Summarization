"""YouTube transcript retrieval."""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse


def extract_video_id(url: str) -> str:
    """Extract a video identifier from common YouTube URL forms."""
    parsed = urlparse(url.strip())
    hostname = (parsed.hostname or "").lower()
    video_id = ""

    if hostname in {"youtu.be", "www.youtu.be"}:
        video_id = parsed.path.strip("/").split("/")[0]
    elif hostname.endswith("youtube.com") or hostname.endswith("youtube-nocookie.com"):
        if parsed.path == "/watch":
            video_id = parse_qs(parsed.query).get("v", [""])[0]
        else:
            match = re.match(r"^/(?:embed|shorts|live)/([^/?]+)", parsed.path)
            video_id = match.group(1) if match else ""

    if not re.fullmatch(r"[\w-]{11}", video_id):
        raise ValueError("Enter a valid YouTube video URL.")

    return video_id


def fetch_transcript(url: str, language_codes: list[str] | None = None) -> str:
    """Fetch a transcript if captions are available for a YouTube video."""
    video_id = extract_video_id(url)
    languages = language_codes or ["en", "hi"]

    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError as exc:
        raise ValueError("YouTube transcript support is not installed.")

    try:
        api = YouTubeTranscriptApi()
        if hasattr(api, "fetch"):
            transcript = api.fetch(video_id, languages=languages)
        else:
            transcript = YouTubeTranscriptApi.get_transcript(
                video_id, languages=languages
            )
        snippets = getattr(transcript, "snippets", transcript)
        text = " ".join(
            str(
                getattr(
                    item, "text", item.get("text", "") if isinstance(item, dict) else ""
                )
            )
            for item in snippets
        )
    except Exception as exc:
        raise ValueError(
            "No accessible transcript was found for this video. Captions maybe diabled or unavailable."
        ) from exc

    if not text.strip():
        raise ValueError("The available transcript was empty.")

    return text.strip()
