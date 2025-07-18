from statistics import mean

import pytest

from sec_doc_tool.chunking.html_splitter import (
    split_html_by_pagebreak,
)


@pytest.mark.parametrize(
    "key", ["edgar/data/1002427/000113322824004879/msif-html7854_485bpos.htm|187"]
)
def test_split_html_by_pagebreaks(key, mock_file_content):
    mock_file_name, num_chunks = key.split("|")
    html_content = mock_file_content(mock_file_name)
    html_chunks, text_chunks = split_html_by_pagebreak(html_content)
    assert len(html_chunks) == len(text_chunks)
    assert len(text_chunks) == int(num_chunks)
    assert mean([len(chunk) for chunk in text_chunks]) < 5000
