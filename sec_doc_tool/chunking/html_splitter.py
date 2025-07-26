import json
import logging
import re
from typing import Iterator
import unicodedata

from bs4 import BeautifulSoup, Comment
import html2text
from pydantic import BaseModel

logger = logging.getLogger(__name__)

_selector_stats: dict[str, dict[str, int]] = {}


def log_selector_stats():
    logger.info("=== logger_selector_stats ===")
    stats = sorted(
        _selector_stats.items(), key=lambda item: item[1]["filings"], reverse=True
    )
    for k, v in stats:
        logger.info(f"{str(v):33} <- {k}")


def sanitize_text(text: str) -> str:
    # 1. Normalize unicode (e.g. accented chars, homoglyphs)
    text = unicodedata.normalize("NFKC", text)

    # 2. Replace various Unicode dashes with ASCII hyphen (-)
    text = re.sub(r"[‐‑‒–—−]", "-", text)  # noqa: RUF001 includes en-dash, em-dash, minus sign, etc.

    # 3. Remove invisible or control characters (except \n or \t optionally)
    text = "".join(
        c for c in text if not unicodedata.category(c).startswith("C") or c in "\n\t"
    )

    # 4. Remove whitespace between dollar sign and number, e.g. "$ 100" → "$100"
    text = re.sub(r"\$\s+(?=\d)", "$", text)

    # 5. Normalize whitespace
    text = re.sub(r"[ \t]+", " ", text)  # normalize horizontal whitespace
    text = re.sub(r"\s*\n\s*", "\n", text)  # remove spaces around line breaks
    text = re.sub(r"\n{2,}", "\n", text)  # collapse multiple line breaks
    text = text.strip()

    return text


def split_html_by_pagebreak(html_content: str, marker: str = "-PAGE-BREAK-") -> list[str]:
    """
    Split html into chunks by using various types of page break marking.

    It uses a position based splitting strategy to handle nested markers in
    a more robust manner.

    Args:
        html_content (str): The HTML content to split.
        marker (str): The marker to use for page breaks. Defaults to "-PAGE-BREAK-".

    Returns:
        tuple: A tuple containing two lists:
            - html_pages: List of HTML content pages split by page breaks.
    """
    html_chunks: list[str] = []

    processed_html = _preprocess_html_for_page_breaks(html_content, marker)
    soup = BeautifulSoup(processed_html, "html.parser")
    markers = soup.find_all("div", class_="page-break-marker")

    if not markers:
        # No page breaks found, treat entire content as one page
        html_chunks.append(html_content)
        return html_chunks

    # Get the root container (body if exists, otherwise the soup itself)
    container = soup.body if soup.body else soup
    html_string = str(container)
    for index, html_content, _ in _content_between_markers(html_string, markers):
        if html_content.strip():
            html_chunks.append(html_content)

    return html_chunks


def _content_between_markers(
    html_content: str, markers: list, want_marker: bool = False
) -> Iterator[tuple[int, str, str]]:
    """
    iterator that yeilds html content between each marker
    it uses a position based splitting strategy to handle nested markers.

    1. find all markers in the html content and mark their positions
    2. use the positions to split the html content
    3. clean up the html fragments and yield

    Args:
        html_content (str): The HTML content to split.
        markers (list): List of BeautifulSoup elements representing page break markers.
        want_marker (bool): If True, include the marker HTML in the output. Defaults to False.

    Yields:
        tuple: A tuple containing:
            - index (int): The index of the chunk.
            - html_content (str): The HTML content chunk.
            - marker_content (str): The HTML content of the marker if want_marker is True,
              otherwise an empty string.
    """
    marker_positions = []
    search_start = 0

    for i, marker in enumerate(markers):
        marker_html = str(marker)
        # Find this specific marker occurrence starting from our last position
        start_pos = html_content.find(marker_html, search_start)
        if start_pos != -1:
            marker_positions.append(
                {
                    "element": marker,
                    "html": marker_html,
                    "string_start": start_pos,
                    "string_end": start_pos + len(marker_html),
                    "index": i,  # Original order for debugging
                }
            )
            # Update search position to after this marker
            search_start = start_pos + len(marker_html)
        else:
            # Marker not found, this shouldn't happen but handle gracefully
            marker_positions.append(
                {
                    "element": marker,
                    "html": marker_html,
                    "string_start": -1,
                    "string_end": -1,
                    "index": i,
                }
            )

    # Sort by string position to ensure correct document order
    marker_positions.sort(
        key=lambda x: x["string_start"] if x["string_start"] != -1 else 999999
    )

    # Split content based on marker positions
    last_end = 0
    index = 0

    for marker_info in marker_positions:
        if marker_info["string_start"] == -1:
            continue  # Skip markers we couldn't locate

        # Extract content before this marker (current page)
        partial_content = html_content[last_end : marker_info["string_start"]]
        marker_content = (
            _clean_html_fragment(str(marker_info["html"])) if want_marker else ""
        )
        if partial_content.strip():
            # Clean up the HTML fragment
            cleaned_content = _clean_html_fragment(partial_content)
            yield index, cleaned_content, marker_content
            index += 1

        last_end = marker_info["string_end"]

    # Add any remaining content after the last marker
    if last_end < len(html_content):
        partial_content = html_content[last_end:]
        if partial_content.strip():
            cleaned_content = _clean_html_fragment(partial_content)
            if cleaned_content.strip():
                yield index, cleaned_content, ""


# ruff: noqa C901
def _preprocess_html_for_page_breaks(html_content: str, marker: str) -> str:
    """
    Preprocess HTML to
    1. remove invisble div
    2. remove comments
    3. insert page break markers before conversion
    """
    global _selector_stats

    # Find and mark page break elements
    page_break_selectors = [
        "hr",  # Horizontal rules
        '[style*="page-break-before"]',
        '[style*="page-break-after"]',
        '[style*="break-before:page"]',
        '[style*="break-before: page"]',
        # ".page-break",
        # ".pagebreak",
        # ".new-page",
    ]
    if not _selector_stats:
        for selector in page_break_selectors:
            _selector_stats[selector] = {"filings": 0, "elements": 0}

    soup = BeautifulSoup(html_content, "html.parser")

    # remove invisible divs
    style_lambda = lambda value: value and "display:none" in value.replace(" ", "")  # noqa: E731
    div_to_remove = soup.find("div", style=style_lambda)
    if div_to_remove:
        div_to_remove.decompose()

    # remove comments
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()

    # find page breaks of various kinds
    page_breaks_found = []

    for selector in page_break_selectors:
        elements = soup.select(selector)
        if elements:
            _selector_stats[selector]["elements"] += len(elements)
            _selector_stats[selector]["filings"] += 1
        page_breaks_found.extend(elements)

    # below logic handles cases like the following:
    # <div style="margin-left: auto; margin-right: auto; width: 100%">
    #     <div style="border-top: Black 2px solid; font-size: 1pt">&nbsp;</div>
    # </div>
    elements = soup.select('[style*="border-top"]')
    elements = [
        el.parent
        for el in elements
        if el.parent
        and el.parent.name == "div"
        and "width: 100%" in el.parent.get("style", "")  # pyright: ignore
        and len(list(el.parent.children)) == 1
    ]
    if elements:
        page_breaks_found.extend(elements)

    # insert page break markers
    for element in page_breaks_found:
        # Create a new tag with our marker
        marker_tag = soup.new_tag("div", **{"class": "page-break-marker"})  # pyright: ignore
        marker_tag.string = marker

        # Insert before the page break element
        if element.parent:
            element.insert_before(marker_tag)

        # Remove HR tags as they're just visual separators
        if element.name == "hr":
            element.decompose()

    return str(soup)


def _clean_html_fragment(html_fragment: str) -> str:
    """
    Clean and wrap HTML fragment to make it valid
    """
    if not html_fragment.strip():
        return ""

    # Try to parse the fragment
    try:
        fragment_soup = BeautifulSoup(html_fragment, "html.parser")

        # If it parsed successfully, return it cleaned up
        if fragment_soup.get_text(strip=True):
            return str(fragment_soup)
        else:
            return ""

    except Exception:
        # If parsing fails, wrap in a div and try again
        try:
            wrapped = f"<div>{html_fragment}</div>"
            fragment_soup = BeautifulSoup(wrapped, "html.parser")
            return str(fragment_soup)
        except Exception:
            # Last resort: return as-is if it has text content
            if html_fragment.strip():
                return f"<div>{html_fragment}</div>"
            return ""
