"""Safe, bounded extraction of readable text from public webpages."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

MAX_RESPONSE_BYTES = 10 * 1024 * 1024
MAX_REDIRECTS = 5
HEADERS = {"User-Agent": "AITextSummarizer/1.0 (+https://streamlit.io)"}


def _validate_public_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Enter a valid public http:// or https:// URL.")
    if parsed.username or parsed.password:
        raise ValueError("URLs containing credentials are not allowed.")

    hostname = parsed.hostname.rstrip(".").lower()
    if (
        hostname == "localhost"
        or hostname.endswith(".localhost")
        or hostname.endswith(".local")
    ):
        raise ValueError("Local and private network URLs are not allowed.")

    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(hostname, None)}
    except socket.gaierror as exc:
        raise ValueError(f"Could not resolve website host: {exc}") from exc

    for address in addresses:
        ip = ipaddress.ip_address(address.split("%", 1)[0])
        if not ip.is_global:
            raise ValueError("Local and private network URLs are not allowed.")

    return url


def fetch_webpage(url: str) -> str:
    """Fetch and extract article-like text while rejecting private-network URLs."""
    current_url = url.strip()
    if len(current_url) > 2048:
        raise ValueError("The URL is too long.")

    for redirect_count in range(MAX_REDIRECTS + 1):
        _validate_public_url(current_url)
        try:
            response = requests.get(
                current_url,
                headers=HEADERS,
                timeout=(5, 20),
                stream=True,
                allow_redirects=False,
            )
        except requests.Timeout as exc:
            raise ValueError("The website request timed out. Try again later.") from exc
        except requests.RequestException as exc:
            raise ValueError(f"Could not fetch this website: {exc}") from exc

        if response.is_redirect or response.is_permanent_redirect:
            location = response.headers.get("Location")
            response.close()

            if not location or redirect_count == MAX_REDIRECTS:
                raise ValueError("This website redirected too many times.")

            current_url = urljoin(current_url, location)
            continue

        try:
            response.raise_for_status()
            content_type = response.headers.get("Content-Type", "").lower()

            if content_type and not any(
                kind in content_type for kind in ("text/html", "application/xhtml")
            ):
                raise ValueError("The URL does not point to an HTML webpage.")

            body = bytearray()
            for chunk in response.iter_content(64 * 1024):
                body.extend(chunk)
                if len(body) > MAX_RESPONSE_BYTES:
                    raise ValueError("The webpage is larger than the 10 MB limit.")

        except requests.RequestException as exc:
            raise ValueError(f"Could not fetch this website: {exc}") from exc
        finally:
            response.close()
        break
    else:
        raise ValueError("The website redirected too many times.")

    soup = BeautifulSoup(bytes(body), "html.parser")
    for node in soup(
        ["script", "style", "noscript", "svg", "nav", "footer", "header", "form"]
    ):
        node.decompose()

    main = soup.find("main") or soup.find("article") or soup.body or soup
    text = " ".join(main.stripped_strings)

    if not text:
        raise ValueError("No readable text was found on that webpage.")
    return text
