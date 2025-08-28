from sec_doc_tool import ChunkedDocument, TextExtractor


def test_doc_chunking():
    # Morgan Stanley Insight Fund
    document = ChunkedDocument.init("1002427", "0001133228-24-004879", refresh=True)

    # LEUTHOLD FUNDS, INC.
    # filing = ChunkedDocument.init("1000351", "0001387131-19-000505")
    assert document and len(document.text_chunk_refs) == len(document.text_chunks)
    assert len(document.text_chunks) == 515
    assert "Statement of Additional Information" in document.text_chunks[20]

    prev_context = document.text_chunks[19][-100:]
    next_context = document.text_chunks[21][:100]
    chunk_with_context = document.get_chunk_with_context(20)
    assert prev_context in chunk_with_context
    assert next_context in chunk_with_context


def test_extract_text_from_doc():
    # Morgan Stanley Insight Fund
    document = ChunkedDocument.init("1002427", "0001133228-24-004879", refresh=True)
    assert document and len(document.text_chunks) == 515

    text_extractor = TextExtractor(["Morgan Stanley Insight Fund"])
    extracted_samples = text_extractor.extract_from_document(
        document, extract_sentences=True, extract_paragraphs=True, use_cache=False
    )
    assert len(extracted_samples) == 26
    assert len([s for s in extracted_samples if s.context_type == "header"]) == 5
