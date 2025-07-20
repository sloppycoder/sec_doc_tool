from unittest.mock import patch

from sec_doc_tool.chunking.text_chunker import (
    _is_line_empty,
    chunk_text,
    trim_html,
)
from sec_doc_tool.edgar import EdgarFiling


@patch("sec_doc_tool.edgar.edgar_file")
def test_chunk_html_filing(mock_edgar_file, mock_file_content):
    mock_edgar_file.side_effect = mock_file_content

    filing = EdgarFiling(cik="1000351", accession_number="0001387131-19-000505")
    filing_path, filing_content = filing.get_doc_content(
        "485BPOS", file_types=["htm", "txt"]
    )[0]

    assert filing_path.endswith(".html") or filing_path.endswith(".htm")

    trimmed_html = trim_html(filing_content)
    chunks = chunk_text(trimmed_html)

    assert len(chunks) == 197
    assert all(chunk and len(chunk) > 10 for chunk in chunks)


@patch("sec_doc_tool.edgar.edgar_file")
def test_chunk_txt_filing(mock_edgar_file, mock_file_content):
    mock_edgar_file.side_effect = mock_file_content

    filing = EdgarFiling(
        cik="1201932",
        accession_number="0000950136-04-001365",
        prefer_index_headers=False,
    )
    filing_path, filing_content = filing.get_doc_content(
        "485BPOS", file_types=["htm", "txt"]
    )[0]

    assert filing_path.endswith(".txt")

    chunks = chunk_text(filing_content)

    assert len(chunks) == 152
    assert all(chunk and len(chunk) > 10 for chunk in chunks)


def test_is_line_empty():
    assert _is_line_empty("   ")
    assert _is_line_empty(" -83-")
    assert _is_line_empty(" wo- wb- xp")
    assert not _is_line_empty(" word ")
