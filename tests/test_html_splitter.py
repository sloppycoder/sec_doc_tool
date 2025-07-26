import pytest

from sec_doc_tool.chunking.html_splitter import (
    split_html_by_pagebreak,
)


@pytest.mark.parametrize(
    "key", ["edgar/data/1002427/000113322824004879/msif-html7854_485bpos.htm|187"]
)
def test_split_html_by_pagebreaks(key, mock_file_content):
    mock_file_name, num_pages = key.split("|")
    html_content = mock_file_content(mock_file_name)
    html_chunks = split_html_by_pagebreak(html_content)
    assert len(html_chunks) == int(num_pages)
