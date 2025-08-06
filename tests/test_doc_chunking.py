from sec_doc_tool import ChunkedDocument


def test_doc_chunking():
    # Morgan Stanley Insight Fund
    filing = ChunkedDocument.init("1002427", "0001133228-24-004879")

    # LEUTHOLD FUNDS, INC.
    # filing = ChunkedDocument.init("1000351", "0001387131-19-000505")
    assert filing and len(filing.text_chunks) == 514
    assert "Statement of Additional Information" in filing.text_chunks[164]

    prev_context = filing.text_chunks[163][-100:]
    next_context = filing.text_chunks[165][:100]
    chunk_with_context = filing.get_chunk_with_context(164)
    assert prev_context in chunk_with_context
    assert next_context in chunk_with_context
