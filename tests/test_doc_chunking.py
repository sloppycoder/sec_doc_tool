from sec_doc_tool import ChunkedDocument


def test_doc_chunking():
    filing = ChunkedDocument.init("1002427", "0001133228-24-004879", refresh=True)
    assert filing and len(filing.chunks) == 365
    assert filing.chunks[0].num == 0
