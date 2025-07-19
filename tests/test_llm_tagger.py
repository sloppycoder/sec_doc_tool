import socket

import pytest

from sec_doc_tool import ChunkedDocument
from sec_doc_tool.tagging.llm_tagger import tag_with_llm


@pytest.mark.skipif(socket.gethostname() != "uno.local", reason="for local testing only")
def test_tag_with_llm():
    filing = ChunkedDocument.load("1002427", "0001133228-24-004879")
    assert filing

    tags, _, _ = tag_with_llm(filing.chunks[10].text)
    assert tags and "Insight Fund" in tags["fund_names"]
