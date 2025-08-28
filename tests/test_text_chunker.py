from unittest.mock import patch

from sec_doc_tool.chunking.html_splitter import split_html_by_pagebreak
from sec_doc_tool.chunking.text_chunker import (
    DEFAULT_TEXT_CHUNK_SIZE,
    _is_line_empty,
    chunk_text,
    trim_html,
)
from sec_doc_tool.edgar import EdgarFiling

# this is extracted from filing 822977/0001193125-24-048017 page B-76
SAMPLE_TEXT_TO_CHUNK = """
policies limiting the circumstances under which cross-trades may be effected between the Fund and another client account. The Investment Adviser conducts periodic reviews of trades for consistency with these policies. For more information about conflicts of interests that may arise in connection with the portfolio manager’s management of the Fund’s investments and the investments of other accounts, see “POTENTIAL CONFLICTS OF INTEREST.”
Portfolio Managers-Compensation
Compensation for portfolio managers of the Investment Adviser is comprised of a base salary and year-end discretionary variable compensation. The base salary is fixed from year to year. Year-end discretionary variable compensation is primarily a function of each portfolio manager’s individual performance and his or her contribution to overall team performance; the performance of GSAM and Goldman Sachs; the team’s net revenues for the past year which in part is derived from advisory fees, and for certain accounts, performance-based fees; and anticipated compensation levels among competitor firms. Portfolio managers are rewarded, in part, for their delivery of investment performance, which is reasonably expected to meet or exceed the expectations of clients and fund shareholders in terms of: excess return over an applicable benchmark, peer group ranking, risk management and factors specific to certain funds such as yield or regional focus. Performance is judged over 1-, 3- and 5-year time horizons.
For compensation purposes, the benchmarks for the Income Builder Fund are Russell 1000 Value Index and the ICE BofAML BB to B U.S. High Yield Constrained Index.
The discretionary variable compensation for portfolio managers is also significantly influenced by various factors, including: (1) effective participation in team research discussions and process; and (2) management of risk in alignment with the targeted risk parameters and investment objectives of a Fund. Other factors may also be considered including: (1) general client/shareholder orientation and (2) teamwork and leadership.
As part of their year-end discretionary variable compensation and subject to certain eligibility requirements, portfolio managers may receive deferred equity-based and similar awards, in the form of: (1) shares of The Goldman Sachs Group, Inc. (restricted stock units); and, (2) for certain portfolio managers, performance-tracking (or “phantom”) shares of a Fund or multiple funds. Performance-tracking shares are designed to provide a rate of return (net of fees) equal to that of the Fund(s) that a portfolio manager manages, or one or more other eligible funds, as determined by senior management, thereby aligning portfolio manager compensation with fund shareholder interests. The awards are subject to vesting requirements, deferred payment and clawback and forfeiture provisions. GSAM, Goldman Sachs or their affiliates expect, but are not required to, hedge the exposure of the performance-tracking shares of a Fund by, among other things, purchasing shares of the relevant Fund(s).
Other Compensation-In addition to base salary and year-end discretionary variable compensation, the Investment Adviser has a number of additional benefits in place including (1) a 401(k) program that enables employees to direct a percentage of their base salary and bonus income into a tax-qualified retirement plan; and (2) investment opportunity programs in which certain professionals may participate subject to certain eligibility requirements.
Portfolio Managers-Portfolio Managers’ Ownership of Securities in the Funds They Manage
The following table shows the portfolio managers’ ownership of securities, including those beneficially owned as well as those owned pursuant to the deferred compensation plan discussed above, in the Funds they manage as of October 31, 2023, unless otherwise noted:
Name of Portfolio Manager | Dollar Range of Equity Securities Beneficially Owned by Portfolio Manager
---|---
Income Builder Fund |
Ron Arons | $100,001-$500,000
Kevin Martens | $100,001-$500,000
Charles “Brook” Dane | Over $1,000,000
Neill Nuttall | $500,001-$1,000,000
Ashish Shah | Over $1,000,000
B-76
"""


@patch("sec_doc_tool.edgar.edgar_file")
def test_chunk_html_filing(mock_edgar_file, mock_file_content):
    mock_edgar_file.side_effect = mock_file_content

    filing = EdgarFiling(cik="1000351", accession_number="0001387131-19-000505")
    filing_path, filing_content = filing.get_doc_content(
        "485BPOS", file_types=["htm", "txt"]
    )[0]

    assert filing_path.endswith(".html") or filing_path.endswith(".htm")

    html_pages = split_html_by_pagebreak(filing_content)
    text_chunks = []
    for _, page in enumerate(html_pages):
        chunks = chunk_text(trim_html(page))
        text_chunks.extend(chunks)

    assert len(html_pages) == 152
    # Table normalization reduces chunk count by keeping table rows together
    assert len(text_chunks) >= 275

    # Verify that chunking produces reasonable sizes
    chunk_sizes = [len(chunk) for chunk in text_chunks]
    avg_size = sum(chunk_sizes) / len(chunk_sizes)

    # Average chunk size should be reasonable
    assert 500 < avg_size < DEFAULT_TEXT_CHUNK_SIZE * 2

    # Should have some variety in chunk sizes (not all identical)
    assert max(chunk_sizes) > min(chunk_sizes)


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

    assert len(chunks) == 192
    assert all(chunk and len(chunk) > 10 for chunk in chunks)


def test_chunk_text_no_gap_in_table():
    """
    the original text contains a markdown table, there was a bug that
    introduces newlines between table rows, this test verify this is fixed
    """
    chunks = chunk_text(SAMPLE_TEXT_TO_CHUNK)
    assert chunks
    assert all(chunk and len(chunk) < DEFAULT_TEXT_CHUNK_SIZE for chunk in chunks)
    # compenstation talbe is at the bottom of the text
    # so it should appear in chunks[1] not in chunks[0]
    # an old bug put it in chunks[0], so we need to make
    # sure regression does not occur.
    comp_text = "Neill Nuttall | $500,001-$1,000,000"
    assert comp_text in chunks[1] and comp_text not in chunks[0]
    assert SAMPLE_TEXT_TO_CHUNK[:50].strip() in chunks[0]
    # check if the table detection logic minimizes gaps between table rows

    max_gap = _max_gap_in_text(chunks[1])
    # With table normalization, gap between rows should be minimal (≤ 2)
    assert max_gap <= 1, f"Table formatting not properly normalized, max gap: {max_gap}"


def test_chunk_html_complex_table(mock_file_content):
    html_page = mock_file_content("html_filing_pages/0001193125-22-229443_page_789.html")
    chunks = chunk_text(trim_html(html_page))

    # After cleaning, gaps should be much smaller (was 9, now should be ≤ 3)
    max_gap = _max_gap_in_text(chunks[1])
    assert max_gap <= 3, f"Table formatting not properly cleaned, max gap: {max_gap}"


def test_is_line_empty():
    assert _is_line_empty("   ")
    assert _is_line_empty(" -83-")
    assert _is_line_empty(" wo- wb- xp")
    assert not _is_line_empty(" word ")


def _max_gap_in_text(text_content: str):
    lines = text_content.split("\n")
    table_lines = [i for i, line in enumerate(lines) if "|" in line and line.strip()]

    # Count gaps between consecutive table rows
    empty_line_gaps = []
    for i in range(len(table_lines) - 1):
        current_row_idx = table_lines[i]
        next_row_idx = table_lines[i + 1]
        gap = next_row_idx - current_row_idx - 1
        if gap > 0:
            empty_line_gaps.append(gap)

    max_gap = max(empty_line_gaps) if empty_line_gaps else 0
    return max_gap
