import logging
import re

import html2text
from bs4 import BeautifulSoup

from ..nlp_model import get_nlp_model
from ..text_utils import TextNormalizer

logger = logging.getLogger(__name__)


DEFAULT_TEXT_CHUNK_SIZE = 2000

# Create a global text normalizer instance
_text_normalizer = TextNormalizer()


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
    Maintains original line order while optimizing sentence splitting.
    Returns the updated current_size.
    """
    # Separate lines that need sentence splitting from those that don't
    lines_needing_splitting = []
    line_processing_map = {}  # Maps line to processing type and order

    for i, line in enumerate(lines):
        if _needs_sentence_splitting(line):
            lines_needing_splitting.append(line)
            line_processing_map[line] = ("split", i)
        else:
            line_processing_map[line] = ("direct", i)

    # Batch process lines that need sentence splitting to get sentence map
    sentence_map = {}
    if lines_needing_splitting:
        sentence_map = _batch_process_lines(lines_needing_splitting)

    # Process all lines in original order
    for line in lines:
        processing_type, _ = line_processing_map[line]

        if processing_type == "direct":
            # Process directly without sentence splitting (fast path)
            current_size = _add_to_chunk(
                line, current_chunk, current_size, chunks, chunk_size
            )
        else:
            # Use pre-computed sentences from batch processing
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

    sanitized_content = _text_normalizer.sanitize_document_text(content)

    # Split content into paragraphs (based on double newline)
    paragraphs = sanitized_content.split("\n\n")

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
        chunks.append(_smart_join_content_pieces(current_chunk))

    # Remove empty chunks and post-process to clean up table formatting
    processed_chunks = []
    for chunk in chunks:
        if chunk.strip() and len(chunk.strip()) > 100:
            processed_chunks.append(_clean_table_formatting_in_chunk(chunk))

    return processed_chunks


def _clean_table_formatting_in_chunk(chunk: str) -> str:
    """
    Clean up excessive empty lines within table sections in the final chunk.
    """
    lines = chunk.split("\n")
    cleaned_lines = []

    i = 0
    while i < len(lines):
        line = lines[i]
        cleaned_lines.append(line)

        # Check if current line is a table row
        is_table_row, _ = _check_table_row(line)

        if is_table_row:
            # Look ahead for the next table row
            j = i + 1
            gap_lines = []

            # Collect lines between this table row and the next
            while j < len(lines):
                next_line = lines[j]
                next_is_table_row, _ = _check_table_row(next_line)

                if next_is_table_row:
                    # Found another table row - check if gap is excessive
                    if len(gap_lines) > 2:
                        # Too many lines between table rows - keep only meaningful content
                        meaningful_lines = []
                        for gap_line in gap_lines:
                            # Keep lines with substantial content (not just spacing/fragments)
                            if (
                                gap_line.strip()
                                and len(gap_line.strip()) > 10
                                and gap_line.strip().lower()
                                not in [
                                    "capital",
                                    "allocation",
                                    "aggressive",
                                    "moderate",
                                    "conservative",
                                ]
                            ):
                                meaningful_lines.append(gap_line)
                            elif not gap_line.strip():  # Keep one empty line
                                if not meaningful_lines or meaningful_lines[-1].strip():
                                    meaningful_lines.append("")

                        # If no meaningful content, just keep one empty line
                        if not any(line.strip() for line in meaningful_lines):
                            meaningful_lines = [""]

                        cleaned_lines.extend(meaningful_lines)
                        logger.debug(
                            f"Cleaned table gap: {len(gap_lines)} lines -> {len(meaningful_lines)} lines"
                        )
                    else:
                        # Normal gap, keep as is
                        cleaned_lines.extend(gap_lines)

                    i = j  # Skip to the next table row
                    break
                else:
                    gap_lines.append(next_line)
                    j += 1
            else:
                # No more table rows found, keep remaining lines
                cleaned_lines.extend(gap_lines)
                i = len(lines)
        else:
            i += 1

    return "\n".join(cleaned_lines)


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


def _smart_join_content_pieces(content_pieces: list[str]) -> str:
    """
    Join content pieces with standard double newline separation.
    Table formatting is cleaned up in post-processing.
    """
    return "\n\n".join(content_pieces)


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
        chunks.append(_smart_join_content_pieces(current_chunk))
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
    line_stripped = line.strip()

    # Check if line contains pipe character(s)
    if "|" not in line_stripped:
        return False, False

    parts = [cell.strip() for cell in line_stripped.split("|")]

    # Accept if:
    # - At least 3 parts (original logic) OR
    # - At least 2 parts with non-empty content OR
    # - Line ends with "|" (single column case)
    if len(parts) >= 3:
        # Original logic for 3+ columns
        pass
    elif len(parts) >= 2:
        # 2 column case - at least one part should have content
        non_empty_parts = [p for p in parts if p.strip()]
        if len(non_empty_parts) == 0:
            return False, False
    elif line_stripped.endswith("|"):
        # Single column ending with | (like "Income Builder Fund |")
        pass
    else:
        return False, False

    cells = [cell.strip() for cell in parts if cell.strip()]
    is_cell_empty = any(
        not s.strip() and bool(re.fullmatch(r"-*", s.strip())) for s in cells
    )

    return True, is_cell_empty
