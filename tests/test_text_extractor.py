import pytest

from sec_doc_tool import (
    ChunkedDocument,
    ExtractedText,
    TextExtractor,
)

# Stub list of mutual fund names - user will fill in later
KNOWN_FUND_NAMES = [
    "Leuthold Core Investment Fund",
    "Leuthold Global Industries Fund",
    "Leuthold Global Fund",
    "Grizzly Short Fund",
    "Leuthold Select Industries Fund",
]


@pytest.fixture
def sample_documents() -> list[ChunkedDocument]:
    """Load sample ChunkedDocuments for testing"""
    documents = []

    # Test document 1: Leuthold (should have fund names from KNOWN_FUND_NAMES)
    doc1 = ChunkedDocument.load("1000351", "0001387131-19-000505")
    if doc1:
        documents.append(doc1)

    # Test document 2: Morgan Stanley (for additional variety)
    doc2 = ChunkedDocument.load("1002427", "0001133228-24-004879")
    if doc2:
        documents.append(doc2)

    assert len(documents) > 0, "Failed to load any test documents"
    return documents


@pytest.fixture
def text_extractor() -> TextExtractor:
    """Create a TextExtractor with stub fund names"""
    return TextExtractor(KNOWN_FUND_NAMES)


def test_text_extraction(
    sample_documents: list[ChunkedDocument], text_extractor: TextExtractor
):
    """Test extracting text segments containing fund names"""
    # Test with first document
    extracted_samples = text_extractor.extract_from_document(
        sample_documents[0], extract_sentences=True, extract_paragraphs=True
    )

    # Basic validation
    assert isinstance(extracted_samples, list)

    # If we find any samples, validate their structure
    if extracted_samples:
        sample = extracted_samples[0]
        assert isinstance(sample, ExtractedText)
        assert isinstance(sample.text, str)
        assert sample.context_type in [
            "narrative",
            "table",
            "header",
            "list",
            "parenthetical",
            "other",
        ]
        assert isinstance(sample.fund_names_found, list)
        assert isinstance(sample.chunk_index, int)
        assert isinstance(sample.sentence_index, int)
        assert sample.chunk_index >= 0


def test_extracted_text_model():
    """Test the ExtractedText Pydantic model"""
    # Test valid creation
    extracted = ExtractedText(
        text="This is a test sentence about Test Fund Alpha.",
        context_type="narrative",
        fund_names_found=["Test Fund Alpha"],
        chunk_index=0,
        sentence_index=1,
    )

    assert extracted.text == "This is a test sentence about Test Fund Alpha."
    assert extracted.context_type == "narrative"
    assert extracted.fund_names_found == ["Test Fund Alpha"]
    assert extracted.chunk_index == 0
    assert extracted.sentence_index == 1

    # Test default value for sentence_index
    extracted_para = ExtractedText(
        text="This is a paragraph.",
        context_type="narrative",
        fund_names_found=["Test Fund Alpha"],
        chunk_index=0,
    )
    assert extracted_para.sentence_index == -1

    # Test serialization
    data = extracted.model_dump()
    assert isinstance(data, dict)
    assert data["text"] == extracted.text

    # Test deserialization
    recreated = ExtractedText.model_validate(data)
    assert recreated.text == extracted.text
    assert recreated.fund_names_found == extracted.fund_names_found


def test_context_detection():
    """Test enhanced context detection with fund name prominence and parenthetical"""
    extractor = TextExtractor(["ABC Growth Fund", "XYZ Bond Fund"])

    # Test parenthetical detection
    parenthetical_text = (
        "The portfolio includes equity investments (ABC Growth Fund) and fixed income."
    )
    context = extractor._detect_context_type(parenthetical_text, {}, ["ABC Growth Fund"])
    assert context == "parenthetical"

    # Test fund name prominence in headers
    header_text = "ABC Growth Fund\nAnnual Report 2024"
    context = extractor._detect_context_type(header_text, {}, ["ABC Growth Fund"])
    assert context == "header"

    # Test normal narrative (fund name present but not prominent)
    narrative_text = (
        "The ABC Growth Fund achieved strong performance this quarter "
        "with returns exceeding expectations."
    )
    context = extractor._detect_context_type(narrative_text, {}, ["ABC Growth Fund"])
    assert context == "narrative"

    # Test table detection still works
    table_text = "|Fund Name|Return|Assets|\n|ABC Growth Fund|8.5%|$50M|"
    context = extractor._detect_context_type(table_text, {}, ["ABC Growth Fund"])
    assert context == "table"
