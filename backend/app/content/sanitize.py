"""Allow-list sanitizing of rich text (FR-PUB-6)."""

import html

import nh3

from app.errors import ApiError

ALLOWED_TAGS = {
    "p", "br", "strong", "b", "em", "i", "u", "h2", "h3",
    "ul", "ol", "li", "a", "blockquote", "code", "pre",
}  # fmt: skip
MAX_TEXT = 5000


def plain_text(body_html: str) -> str:
    """The text of sanitized HTML, with a space where a tag was."""
    spaced = body_html.replace("<", " <")
    return " ".join(html.unescape(nh3.clean(spaced, tags=set())).split())


def clean_body(body_html: str) -> str:
    """Remove everything not on the allow-list and check the length of the visible text."""
    clean = nh3.clean(
        body_html,
        tags=ALLOWED_TAGS,
        attributes={"a": {"href"}},
        url_schemes={"http", "https", "mailto"},
    )
    text = plain_text(clean)
    if not text:
        raise ApiError("EMPTY_CONTENT")
    if len(text) > MAX_TEXT:
        raise ApiError("CONTENT_TOO_LONG")
    return clean
