from sec_doc_tool import ChunkedDocument
from sec_doc_tool.tagging.text_tagger import tag_with_ner


def test_tag_with_ner():
    filing = ChunkedDocument.load("1002427", "0001133228-24-004879")
    assert filing

    tags = tag_with_ner(filing.chunks[10].text)
    assert tags and tags["person_unique"] > 5
