"""Merging Yjs updates and converting a Yjs document to HTML (ADR-002)."""

from html import escape

from pycrdt import Doc, XmlElement, XmlFragment, XmlText

FRAGMENT = "default"  # name used by TipTap's collaboration extension
TAGS = {
    "paragraph": "p",
    "bulletList": "ul",
    "orderedList": "ol",
    "listItem": "li",
    "blockquote": "blockquote",
    "hardBreak": "br",
}
MARKS = {"bold": "strong", "italic": "em", "underline": "u", "code": "code"}


def load(state: bytes) -> Doc:
    """Document from stored state."""
    doc: Doc = Doc()
    doc.apply_update(state)
    return doc


def empty_state() -> bytes:
    """State of a new document."""
    return Doc().get_update()


def merge(state: bytes, update: bytes) -> bytes:
    """Stored state plus one client update. Merging is commutative, so order does not matter."""
    doc = load(state)
    doc.apply_update(update)
    return doc.get_update()


def to_html(state: bytes) -> str:
    """HTML of the document. The caller sanitizes it like any other user input."""
    return "".join(_node(child) for child in load(state).get(FRAGMENT, type=XmlFragment).children)


def _node(node: XmlElement | XmlText) -> str:
    if isinstance(node, XmlText):
        return "".join(_text(str(text), marks or {}) for text, marks in node.diff())
    inner = "".join(_node(child) for child in node.children)
    if node.tag == "codeBlock":
        return f"<pre><code>{inner}</code></pre>"
    tag = f"h{dict(node.attributes)['level']:.0f}" if node.tag == "heading" else TAGS.get(node.tag, "p")
    return "<br>" if tag == "br" else f"<{tag}>{inner}</{tag}>"


def _text(text: str, marks: dict) -> str:
    result = escape(text)
    for mark, attributes in marks.items():
        if mark in MARKS:
            result = f"<{MARKS[mark]}>{result}</{MARKS[mark]}>"
        elif mark == "link":
            result = f'<a href="{escape(attributes["href"])}">{result}</a>'
    return result
