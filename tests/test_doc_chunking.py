from sec_doc_tool import ChunkedDocument


def test_doc_chunking():
    # Morgan Stanley Insight Fund
    filing = ChunkedDocument.init("1002427", "0001133228-24-004879")
    # LEUTHOLD FUNDS, INC.
    # filing = ChunkedDocument.init("1000351", "0001387131-19-000505")
    assert filing and len(filing.chunks) == 365
    assert "Statement of Additional Information" in filing.chunks[165].text
