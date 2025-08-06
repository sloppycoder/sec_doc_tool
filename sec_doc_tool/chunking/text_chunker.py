import logging
import re
import unicodedata

import html2text
from bs4 import BeautifulSoup

from ..nlp_model import get_nlp_model

logger = logging.getLogger(__name__)


DEFAULT_TEXT_CHUNK_SIZE = 2000


# these characters in fund name will be removed
# ™ 2122 trade mark
# ® 00ae registered trade mark
_chars_to_remove = "\u2122\u00ae"
_translation_table = str.maketrans("", "", _chars_to_remove)


def _needs_sentence_splitting(line: str) -> bool:
    """
    Check if line needs sophisticated sentence splitting.
    Skip tables, headers, short lines, etc.
    """
    line = line.strip()

    # Skip very short lines
    if len(line) < 50:
        return False

    # Skip lines that look like tables (contain multiple | or tabs)
    if line.count("|") >= 2 or line.count("\t") >= 2:
        return False

    # Skip lines that are mostly uppercase (likely headers)
    if len(line) > 20 and sum(1 for c in line if c.isupper()) / len(line) > 0.7:
        return False

    # Skip lines with mostly numbers and special characters
    alphanumeric_count = sum(1 for c in line if c.isalnum())
    if alphanumeric_count / len(line) < 0.5:
        return False

    # Skip lines that don't contain sentence-ending punctuation
    if not any(punct in line for punct in ".!?"):
        return False

    return True


def _batch_process_lines(lines: list[str]) -> dict[str, list[str]]:
    """
    Process multiple lines at once with SpaCy for better performance.
    Returns a mapping from original line to its sentences.
    """
    if not lines:
        return {}

    nlp = get_nlp_model()

    # Create a mapping to track which sentences belong to which lines
    line_markers = []
    combined_parts = []

    for i, line in enumerate(lines):
        line_markers.append((i, len(combined_parts)))
        combined_parts.append(line)

    # Process all lines together
    combined_text = "\n".join(combined_parts)
    doc = nlp(combined_text)

    # Map sentences back to original lines
    result = {}
    sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]

    # Simple approach: split sentences proportionally back to lines
    # This is an approximation but much faster than individual processing
    for i, line in enumerate(lines):
        # Estimate how many sentences this line should get
        line_length = len(line)
        total_length = sum(len(line_text) for line_text in lines)

        if total_length > 0:
            expected_sentences = max(1, int(len(sentences) * line_length / total_length))
            start_idx = sum(
                max(1, int(len(sentences) * len(lines[j]) / total_length))
                for j in range(i)
            )
            end_idx = min(len(sentences), start_idx + expected_sentences)
            result[line] = (
                sentences[start_idx:end_idx] if start_idx < len(sentences) else [line]
            )
        else:
            result[line] = [line]

    return result


def _process_lines_batch(
    lines: list[str],
    current_chunk: list[str],
    current_size: int,
    chunks: list[str],
    chunk_size: int,
) -> int:
    """
    Process a batch of lines using conditional and batch processing.
    Returns the updated current_size.
    """
    # Separate lines that need sentence splitting from those that don't
    lines_needing_splitting = []
    lines_not_needing_splitting = []

    for line in lines:
        if _needs_sentence_splitting(line):
            lines_needing_splitting.append(line)
        else:
            lines_not_needing_splitting.append(line)

    # Process lines that don't need sentence splitting (fast path)
    for line in lines_not_needing_splitting:
        current_size = _add_to_chunk(
            line, current_chunk, current_size, chunks, chunk_size
        )

    # Batch process lines that need sentence splitting
    if lines_needing_splitting:
        sentence_map = _batch_process_lines(lines_needing_splitting)
        for line in lines_needing_splitting:
            sentences = sentence_map.get(line, [line])
            for sentence in sentences:
                if sentence.strip():  # Skip empty sentences
                    current_size = _add_to_chunk(
                        sentence, current_chunk, current_size, chunks, chunk_size
                    )

    return current_size


def chunk_text(content: str, chunk_size: int = DEFAULT_TEXT_CHUNK_SIZE) -> list[str]:
    """
    Split a text into chunks of size chunk_size

    Args:
        content (str): The text to split into chunks
        chunk_size (int): The size of each chunk

    Returns:
        list[str]: A list of text chunks
    """

    logger.debug("chunk_text: starting processing")

    chunks = []
    current_chunk = []
    current_size = 0

    santized_content = _sanitize_text(content)

    # Split content into paragraphs (based on double newline)
    paragraphs = santized_content.split("\n\n")

    for paragraph in paragraphs:
        # Detect potential tables by splitting into lines
        lines = paragraph.strip().split("\n")
        lines = [line.strip() for line in lines if not _is_line_empty(line)]

        # Buffer to collect a single Markdown table
        table_buffer = []
        # Buffer to collect lines that need sentence splitting
        lines_to_process = []

        for line in lines:
            is_table_row, is_empty_table_row = _check_table_row(line)
            if is_table_row:
                # Flush any pending lines for batch processing
                if lines_to_process:
                    current_size = _process_lines_batch(
                        lines_to_process, current_chunk, current_size, chunks, chunk_size
                    )
                    lines_to_process = []

                # Collect the line into the table buffer, only if the row is not empty
                if not is_empty_table_row:
                    table_buffer.append(line)
            else:
                # If line is not a table, flush the table buffer first
                if table_buffer:
                    table_content = "\n".join(table_buffer)
                    current_size = _add_to_chunk(
                        table_content, current_chunk, current_size, chunks, chunk_size
                    )
                    table_buffer = []

                # Collect non-table lines for batch processing
                lines_to_process.append(line)

        # Process any remaining lines in batch
        if lines_to_process:
            current_size = _process_lines_batch(
                lines_to_process, current_chunk, current_size, chunks, chunk_size
            )

        # Flush any remaining table in the buffer
        if table_buffer:
            table_content = "\n".join(table_buffer)
            current_size = _add_to_chunk(
                table_content, current_chunk, current_size, chunks, chunk_size
            )

    # Add any remaining content
    if current_chunk:
        chunks.append("\n\n".join(current_chunk))

    # Remove empty chunks
    return [chunk for chunk in chunks if chunk.strip() and len(chunk.strip()) > 100]


def trim_html(content: str) -> str:
    """
    remove the hidden div and convert the rest of html into text
    """
    if not content:
        return ""

    soup = BeautifulSoup(content, "html.parser")

    style_lambda = lambda value: value and "display:none" in value.replace(" ", "")  # noqa
    div_to_remove = soup.find("div", style=style_lambda)

    if div_to_remove:
        div_to_remove.decompose()  # type: ignore

    return _text2html(str(soup))


def _text2html(html_content: str):
    converter = html2text.HTML2Text()
    converter.ignore_links = False
    converter.ignore_images = True
    converter.ignore_emphasis = True
    converter.body_width = 0
    return converter.handle(html_content)


def _add_to_chunk(
    content_piece: str,
    current_chunk: list[str],
    current_size: int,
    chunks: list[str],
    chunk_size: int,
) -> int:
    """
    Add a piece of content to the current chunk or start a new one if the size exceeds
    chunk_size.

    Args:
        content_piece (str): The content to add.
        current_chunk (list[str]): The current chunk being built.
        current_size (int): The size of the current chunk.
        chunks (list[str]): The list of completed chunks.

    Returns:
        int: The updated size of the current chunk.
    """
    content_size = len(content_piece)
    if current_size + content_size > chunk_size:
        # Save current chunk and start a new one
        chunks.append("\n\n".join(current_chunk))
        current_chunk[:] = [content_piece]  # Reset current_chunk with new content
        return content_size
    else:
        current_chunk.append(content_piece)
        return current_size + content_size


def _is_line_empty(line: str) -> bool:
    content = line.strip()
    if not content:
        return True

    if len(content) < 5 and not any(char.isalpha() for char in content):
        return True

    words = re.findall(r"\b\w+\b", content)
    if all(len(word) <= 2 for word in words):
        return True

    return False


def _check_table_row(line: str) -> tuple[bool, bool]:
    """
    Check if a line is a table row in a Markdown table
    And if the table row is empty
    return [is_table_row, is_table_row_empty]
    """
    parts = [cell.strip() for cell in line.strip().split("|")]

    if len(parts) < 3:
        return False, False

    cells = [cell.strip() for cell in parts if cell.strip()]
    is_cell_empty = any(
        not s.strip() and bool(re.fullmatch(r"-*", s.strip())) for s in cells
    )

    return True, is_cell_empty


def _sanitize_text(text: str) -> str:
    # 1. Normalize unicode (e.g. accented chars, homoglyphs)
    text = unicodedata.normalize("NFKC", text)

    # 2. Replace various Unicode dashes with ASCII hyphen (-) and remove special symbols
    text = re.sub(r"[‐‑‒–—−]", "-", text)  # noqa: RUF001 includes en-dash, em-dash, minus sign, etc.
    text = text.translate(_translation_table)

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


# def _add_context_from_neighbors(chunks: list[str], context_size: int = 500) -> list[str]:
#     """
#     Add context from neighboring chunks to each chunk.
#     """
#     if not chunks:
#         return chunks

#     # Create a new list to hold the updated chunks
#     updated_chunks = []

#     for i, chunk in enumerate(chunks):
#         # Get the surrounding context
#         prev_chunk = chunks[i - 1] if i > 0 else ""
#         next_chunk = chunks[i + 1] if i < len(chunks) - 1 else ""

#         # Combine the context with the current chunk
#         updated_chunk = (
#             f"{prev_chunk[-1 * context_size :]}\n\n{chunk}\n\n{next_chunk[:context_size]}"
#         )
#         updated_chunks.append(updated_chunk)

#     return updated_chunks
