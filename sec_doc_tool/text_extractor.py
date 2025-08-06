import json
import logging
import re
from typing import Any

import spacy
from pydantic import BaseModel, Field

from . import ChunkedDocument, load_obj_from_cache, write_obj_to_cache

logger = logging.getLogger(__name__)


class ExtractedText(BaseModel):
    """Represents an extracted text segment with context"""

    text: str
    context_type: str  # 'narrative', 'table', 'header', 'list', 'other'
    fund_names_found: list[str]
    chunk_index: int
    sentence_index: int = Field(default=-1)  # -1 for paragraph-level extraction
    document_key: str = Field(default="")  # Format: "{cik}/{accession_number}"
    quality_score: float = Field(default=0.0)  # Quality score for filtering


class TextExtractor:
    """Extracts sentences and paragraphs containing fund names from ChunkedDocument"""

    def __init__(self, fund_names: list[str], lazy_load_nlp: bool = False):
        """
        Initialize with list of fund names to search for

        Args:
            fund_names: List of mutual fund names to extract
            lazy_load_nlp: If True, delay spaCy model loading until first use
        """
        self.fund_names = fund_names
        self.fund_names_lower = [name.lower() for name in fund_names]
        self._nlp: Any | None = None
        self.lazy_load_nlp = lazy_load_nlp

        if not lazy_load_nlp:
            self._load_nlp()

    def _load_nlp(self):
        """Load spaCy model for sentence segmentation"""
        if self._nlp is None:
            try:
                self._nlp = spacy.load("en_core_web_lg")
            except OSError:
                # Fallback to smaller model if large one not available
                self._nlp = spacy.load("en_core_web_sm")

            # Disable unnecessary pipeline components for speed, but keep sentencizer
            self._nlp.disable_pipes(["tagger", "ner", "lemmatizer"])

            # Add sentencizer if parser is disabled (for sentence segmentation)
            if "parser" not in self._nlp.pipe_names:
                self._nlp.add_pipe("sentencizer")

    @property
    def nlp(self) -> Any:
        """Lazy-load spaCy model if needed"""
        if self._nlp is None:
            self._load_nlp()
        assert self._nlp is not None  # For type checker
        return self._nlp

    def _generate_cache_key(self, document: ChunkedDocument) -> str:
        """
        Generate a unique cache key for a document

        Args:
            document: ChunkedDocument to process

        Returns:
            String cache key based on CIK and accession number
        """
        return f"{document.cik}/{document.accession_number}"

    def _get_cache_file_path(self, cache_key: str) -> str:
        return f"extracted_texts/{cache_key}.json"

    def _save_extracted_texts_to_cache(
        self, cache_key: str, extracted_texts: list[ExtractedText]
    ) -> None:
        """
        Save extracted texts to cache file

        Args:
            cache_key: Unique cache key
            extracted_texts: List of ExtractedText objects to cache
        """
        try:
            # Convert to serializable format
            cache_data = [text.model_dump() for text in extracted_texts]

            # Serialize to JSON bytes
            json_str = json.dumps(cache_data, indent=2, ensure_ascii=False)
            json_bytes = json_str.encode("utf-8")

            # Use sec_doc_tool.file_utils to write cache
            cache_file_path = self._get_cache_file_path(cache_key)
            success = write_obj_to_cache(cache_file_path, json_bytes)
            if not success:
                logger.warning(f"Failed to write cache for key {cache_key}")

        except Exception as e:
            logger.warning(f"Failed to save cache for key {cache_key}: {e}")

    def _load_extracted_texts_from_cache(
        self, cache_key: str
    ) -> list[ExtractedText] | None:
        """
        Load extracted texts from cache file

        Args:
            cache_key: Unique cache key

        Returns:
            List of ExtractedText objects if cache exists, None otherwise
        """
        try:
            # Use sec_doc_tool.file_utils to load cache
            cache_file_path = self._get_cache_file_path(cache_key)
            json_bytes = load_obj_from_cache(cache_file_path)
            if json_bytes is None:
                return None

            # Deserialize from JSON bytes
            json_str = json_bytes.decode("utf-8")
            cache_data = json.loads(json_str)

            # Convert back to ExtractedText objects
            return [ExtractedText(**item) for item in cache_data]

        except Exception as e:
            logger.warning(f"Failed to load cache for key {cache_key}: {e}")
            return None

    def _contains_fund_name(self, text: str) -> list[str]:
        """
        Check if text contains any fund names

        Args:
            text: Text to search

        Returns:
            List of fund names found in the text
        """
        text_lower = text.lower()
        found_names = []

        for i, fund_name in enumerate(self.fund_names_lower):
            if fund_name in text_lower:
                found_names.append(self.fund_names[i])

        return found_names

    # ruff: noqa: C901
    def _detect_context_type(
        self, text: str, chunk_tags: dict[str, Any], fund_names_found: list[str]
    ) -> str:
        """
        Detect the context type of the text segment

        Args:
            text: Text segment to analyze
            chunk_tags: Tags associated with the chunk
            fund_names_found: Fund names found in this text (for prominence analysis)

        Returns:
            Context type: 'narrative', 'table', 'header', 'list', 'parenthetical', 'other'
        """
        text_clean = text.strip()

        # Check chunk tags first
        if chunk_tags:
            if chunk_tags.get("is_table", False):
                return "table"
            if chunk_tags.get("is_header", False):
                return "header"
            if chunk_tags.get("is_list", False):
                return "list"

        # Check for parenthetical mentions (fund name in parentheses)
        for fund_name in fund_names_found:
            if f"({fund_name})" in text or f"({fund_name.upper()})" in text:
                return "parenthetical"

        # Check for fund name prominence in headers (fund name dominates the line)
        lines = text.split("\n")
        for line in lines:
            line_stripped = line.strip()
            if len(line_stripped) > 0:
                for fund_name in fund_names_found:
                    if fund_name in line and len(fund_name) / len(line_stripped) > 0.6:
                        return "header"

        # Rule-based detection for context types

        # Table detection patterns
        table_patterns = [
            r"\|\s*[^|]+\s*\|",  # pipe-separated
            r"\t.*\t",  # tab-separated
            r"^\s*\$[\d,]+\.?\d*\s*$",  # monetary amounts
            r"^\s*\d+\.\d+%\s*$",  # percentages
            r"\b(?:Total|Subtotal|Sum)\b.*\$",  # totals with amounts
        ]

        if any(
            re.search(pattern, text_clean, re.MULTILINE | re.IGNORECASE)
            for pattern in table_patterns
        ):
            return "table"

        # Header detection patterns
        header_patterns = [
            r"^[A-Z\s]{3,}$",  # All caps text
            r"^\d+\.\s+[A-Z]",  # Numbered sections
            r"^[A-Z][^.!?]*:$",  # Section headers ending with colon
            r"^PART\s+[IVX]+",  # SEC form parts
            r"^Item\s+\d+",  # SEC form items
        ]

        if any(
            re.search(pattern, text_clean, re.MULTILINE) for pattern in header_patterns
        ):
            return "header"

        # List detection patterns
        list_patterns = [
            r"^\s*[•·▪▫]\s+",  # Bullet points
            r"^\s*\d+\.\s+",  # Numbered lists
            r"^\s*[a-z]\)\s+",  # Lettered lists
            r"^\s*-\s+",  # Dash lists
        ]

        if any(re.search(pattern, text_clean, re.MULTILINE) for pattern in list_patterns):
            return "list"

        # Default to narrative for longer, sentence-like text
        if len(text_clean) > 50 and (
            "." in text_clean or "!" in text_clean or "?" in text_clean
        ):
            return "narrative"

        return "other"

    def _extract_sentences(
        self, text: str, chunk_index: int, chunk_tags: dict[str, Any], document_key: str
    ) -> list[ExtractedText]:
        """
        Extract sentences containing fund names from text

        Args:
            text: Text to process
            chunk_index: Index of the chunk
            chunk_tags: Tags associated with the chunk

        Returns:
            List of ExtractedText objects for sentences
        """
        extracted = []

        # Process text with spaCy for sentence segmentation
        nlp_model = self.nlp  # This will lazy-load if needed
        doc = nlp_model(text)

        for sent_idx, sent in enumerate(doc.sents):
            sent_text = sent.text.strip()

            # Skip very short sentences
            if len(sent_text) < 20:
                continue

            fund_names_found = self._contains_fund_name(sent_text)

            if fund_names_found:
                context_type = self._detect_context_type(
                    sent_text, chunk_tags, fund_names_found
                )

                extracted.append(
                    ExtractedText(
                        text=sent_text,
                        context_type=context_type,
                        fund_names_found=fund_names_found,
                        chunk_index=chunk_index,
                        sentence_index=sent_idx,
                        document_key=document_key,
                    )
                )

        return extracted

    def _extract_paragraphs(
        self, text: str, chunk_index: int, chunk_tags: dict[str, Any], document_key: str
    ) -> list[ExtractedText]:
        """
        Extract paragraphs containing fund names from text

        Args:
            text: Text to process
            chunk_index: Index of the chunk
            chunk_tags: Tags associated with the chunk

        Returns:
            List of ExtractedText objects for paragraphs
        """
        extracted = []

        # Split text into paragraphs (double newlines or similar patterns)
        paragraphs = re.split(r"\n\s*\n", text)

        for para in paragraphs:
            para_text = para.strip()

            # Skip very short paragraphs
            if len(para_text) < 50:
                continue

            fund_names_found = self._contains_fund_name(para_text)

            if fund_names_found:
                context_type = self._detect_context_type(
                    para_text, chunk_tags, fund_names_found
                )

                extracted.append(
                    ExtractedText(
                        text=para_text,
                        context_type=context_type,
                        fund_names_found=fund_names_found,
                        chunk_index=chunk_index,
                        sentence_index=-1,  # Indicates paragraph-level
                        document_key=document_key,
                    )
                )

        return extracted

    def extract_from_document(
        self,
        document: ChunkedDocument,
        extract_sentences: bool = True,
        extract_paragraphs: bool = True,
    ) -> list[ExtractedText]:
        """
        Extract text segments containing fund names from a ChunkedDocument

        Args:
            document: ChunkedDocument to process
            extract_sentences: Whether to extract sentences
            extract_paragraphs: Whether to extract paragraphs

        Returns:
            List of ExtractedText objects
        """
        # Generate cache key for this document
        cache_key = self._generate_cache_key(document)

        # Try to load from cache first
        cached_results = self._load_extracted_texts_from_cache(cache_key)
        if cached_results is not None:
            logger.info(
                f"Loaded cached results for {document.cik}/{document.accession_number}: "
                f"{len(cached_results)} segments"
            )
            return cached_results

        # Cache miss - perform extraction
        logger.info(
            f"Cache miss for {document.cik}/{document.accession_number}, "
            f"performing extraction"
        )

        all_extracted = []
        document_key = f"{document.cik}/{document.accession_number}"

        for chunk_idx, chunk_text in enumerate(document.text_chunks):
            # Get chunk tags if available
            chunk_tags = {}
            if chunk_idx < len(document.chunk_tags):
                chunk_tags = document.chunk_tags[chunk_idx]

            # Extract sentences if requested
            if extract_sentences:
                sentences = self._extract_sentences(
                    chunk_text, chunk_idx, chunk_tags, document_key
                )
                all_extracted.extend(sentences)

            # Extract paragraphs if requested
            if extract_paragraphs:
                paragraphs = self._extract_paragraphs(
                    chunk_text, chunk_idx, chunk_tags, document_key
                )
                all_extracted.extend(paragraphs)

        # Save results to cache
        self._save_extracted_texts_to_cache(cache_key, all_extracted)

        logger.info(
            f"Completed extraction for {document.cik}/{document.accession_number}: "
            f"{len(all_extracted)} segments"
        )

        return all_extracted

    def extract_from_documents(
        self,
        documents: list[ChunkedDocument],
        extract_sentences: bool = True,
        extract_paragraphs: bool = True,
    ) -> list[ExtractedText]:
        """
        Extract text segments from multiple ChunkedDocuments

        Args:
            documents: List of ChunkedDocument objects to process
            extract_sentences: Whether to extract sentences
            extract_paragraphs: Whether to extract paragraphs

        Returns:
            List of ExtractedText objects from all documents
        """
        all_extracted = []

        for document in documents:
            extracted = self.extract_from_document(
                document, extract_sentences, extract_paragraphs
            )
            all_extracted.extend(extracted)

        return all_extracted


class QueueHandler(logging.Handler):
    """Custom logging handler that sends log records to a multiprocessing queue"""

    def __init__(self, queue):
        super().__init__()
        self.queue = queue

    def emit(self, record):
        try:
            self.queue.put(record)
        except Exception:
            # Silently ignore errors to avoid breaking the worker
            pass


def _calculate_quality_score_worker(extracted: "ExtractedText") -> float:
    """
    Calculate quality score for an extracted text sample in worker process

    This is a simplified version of DiversityFilter._calculate_quality_score
    to avoid importing the entire pipeline module in workers.
    """
    text = extracted.text
    score = 0.0

    # Length score (prefer medium-length texts)
    length = len(text)
    if 50 <= length <= 300:
        score += 0.3
    elif 300 < length <= 500:
        score += 0.2
    elif length > 500:
        score += 0.1

    # Grammar/structure score
    sentence_count = len(re.findall(r"[.!?]+", text))
    if sentence_count >= 1:
        score += 0.2

    # Capitalization score (prefer proper sentence case)
    if text[0].isupper() if text else False:
        score += 0.1

    # Fund name prominence score (prefer texts where fund names are clearly mentioned)
    fund_mentions = len(extracted.fund_names_found)
    if fund_mentions == 1:
        score += 0.3  # Single fund mention is ideal
    elif fund_mentions == 2:
        score += 0.2
    elif fund_mentions > 2:
        score += 0.1

    # Context type scoring
    context_scores = {
        "narrative": 0.3,  # Prefer narrative text
        "parenthetical": 0.25,  # Parenthetical mentions are quite valuable
        "table": 0.2,  # Tables can be useful but less preferred
        "list": 0.15,  # Lists are okay
        "header": 0.1,  # Headers are less useful
        "other": 0.05,  # Other types least preferred
    }
    score += context_scores.get(extracted.context_type, 0)

    # Penalty for very repetitive text
    words = text.lower().split()
    if len(words) > 0:
        unique_words = len(set(words))
        repetition_ratio = unique_words / len(words)
        if repetition_ratio < 0.5:
            score *= 0.7  # Penalty for repetitive text

    # Penalty for text with too many numbers/symbols
    alpha_ratio = sum(c.isalpha() or c.isspace() for c in text) / len(text)
    if alpha_ratio < 0.7:
        score *= 0.8

    return min(score, 1.0)


def _process_document_worker(args):
    """
    Worker function for multiprocessing document extraction with logging support

    Args:
        args: Tuple of (
            document_key, fund_names, extract_sentences, extract_paragraphs, index,
            total_documents, document_fund_names
        )

    Returns:
        List of ExtractedText objects or None on failure
    """
    (
        document_key,
        fund_names,
        extract_sentences,
        extract_paragraphs,
        index,
        total_documents,
        document_fund_names,
    ) = args

    try:
        cik, accession_number = document_key.split("/")
        logger.info(
            f"Worker starting for processing {index}/{total_documents} {document_key}"
        )

        # Load the document inside the worker
        document = ChunkedDocument.init(cik, accession_number)
        if not document:
            logger.error(f"Worker failed to load document: {document_key}")
            return None

        # Save memory by clearing html_pages
        document.html_pages = []

        # Create TextExtractor with lazy loading for this process
        extractor = TextExtractor(fund_names, lazy_load_nlp=True)

        extracted = extractor.extract_from_document(
            document, extract_sentences, extract_paragraphs
        )

        # Calculate quality scores for all samples
        for sample in extracted:
            sample.quality_score = _calculate_quality_score_worker(sample)

        logger.info(
            f"Worker completed: {document_key}, Extracted {len(extracted)} segments"
        )

        return extracted

    except Exception as e:
        logger.error(f"Worker failed: {document_key}, Error: {e}")
        return None
