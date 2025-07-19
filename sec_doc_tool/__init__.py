from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

from sec_doc_tool.chunking.html_splitter import split_html_by_pagebreak
from sec_doc_tool.chunking.text_chunker import chunk_text
from sec_doc_tool.edgar import EdgarFiling
from sec_doc_tool.file_cache import load_obj_from_cache, write_obj_to_cache
from sec_doc_tool.tagging.llm_tagger import tag_with_llm
from sec_doc_tool.tagging.text_tagger import tag_with_ner

logger = logging.getLogger(__name__)


MAX_CHUNK_SIZE = 2000


class DocumentChunk(BaseModel):
    cik: str
    accession_number: str
    num: int = Field(ge=0)
    text: str
    html: str
    tags: dict[str, Any] = {}
    # below are for internal use only
    _llm_cost: float = 0.0
    _llm_token_count: int = 0

    @property
    def is_tagged(self, source: str = "all") -> bool:
        """
        tags uses <source>/<tag_name> as key
        """
        if source is None or source == "":
            return False

        if source == "all":
            return len(self.tags) > 0
        else:
            return any(k.startswith(f"{source}/") for k in self.tags)

    def tag(self) -> dict[str, Any]:
        """
        Add tags to a specific chunk
        """
        tags = tag_with_ner(self.text)
        ner_tags = {f"ner/{k}": v for k, v in tags.items()}

        tags, self._llm_token_count, self._llm_cost = tag_with_llm(self.text)
        llm_tags = {f"llm/{k}": v for k, v in tags.items()}

        self.tags = {**ner_tags, **llm_tags}
        logger.debug(
            f"Tagged chunk {self.num} of filing {self.cik}/{self.accession_number} with {self.tags}"
        )
        return self.tags


class ChunkedDocument(BaseModel):
    """
    Represents a filing that has been split into chunks
    """

    cik: str
    accession_number: str
    date_filed: str
    chunks: list[DocumentChunk] = []

    @classmethod
    def load(
        cls,
        cik: str,
        accession_number: str,
    ) -> "ChunkedDocument|None":
        """
        Load an object from cache if it exists
        None if cached file doesn't exist or cannot be valided
        """
        try:
            cache_file_path = f"chunked_filing/{cik}/{accession_number}.json"
            data = load_obj_from_cache(cache_file_path)
            if data:
                return ChunkedDocument.model_validate_json(data)
        except Exception as e:
            logger.info(f"Failed to load ChunkedFiling from cache: {e}")
            return None

    def add_chunk(self, num: int, text: str, html: str = "") -> DocumentChunk:
        """
        Add a chunk to the filing
        """
        chunk = DocumentChunk(
            num=num,
            text=text,
            html=html,
            cik=self.cik,
            accession_number=self.accession_number,
        )
        self.chunks.append(chunk)
        return chunk

    def tag_all_chunks(self, limit: int = 999999):
        """parameter limit is for testing only"""
        llm_token_count, llm_cost = 0, 0.0
        for i, chunk in enumerate(self.chunks[:limit]):
            chunk.tag()
            llm_token_count += chunk._llm_token_count
            llm_cost += chunk._llm_cost
            logger.info(
                f"tagged {self.cik}/{self.accession_number} chunk {i} spent {llm_token_count} tokens costs {llm_cost}"
            )
        return llm_token_count, llm_cost

    @classmethod
    def init(
        cls,
        cik: str,
        accession_number: str,
        refresh: bool = False,
    ) -> "ChunkedDocument|None":
        """
        Initialize a ChunkedFiling object by loading it from cache or
        creating it from an EdgarFiling.
        """
        if not refresh:
            obj = cls.load(
                cik=cik,
                accession_number=accession_number,
            )
            if obj:
                logger.debug(
                    f"Loaded ChunkedFiling({cik}/{accession_number}) with {len(obj.chunks)} chunks from cache"
                )
                return obj

        edgar_filing = EdgarFiling(cik=cik, accession_number=accession_number)
        doc_contents = edgar_filing.get_doc_content("485BPOS", file_types=["htm", "txt"])
        if not doc_contents:
            logger.info("No HTML or TXT content found for {cik}/{accession_number}")
            return None

        doc_path, doc_content = doc_contents[0]

        if doc_path.endswith(".htm"):
            html_chunks, text_chunks = split_html_by_pagebreak(doc_content)
        elif doc_path.endswith(".txt"):
            html_chunks, text_chunks = [], chunk_text(doc_content)
        else:
            raise ValueError(f"Unsupported document type: {doc_path}")

        filing = ChunkedDocument(
            cik=cik,
            accession_number=accession_number,
            date_filed=edgar_filing.date_filed,
        )
        for i in range(len(text_chunks)):
            filing.add_chunk(
                i,
                text=text_chunks[i],
                html=html_chunks[i] if len(html_chunks) >= i else "",
            )
        filing._save()

        logger.debug(
            f"Created new ChunkedFiling({cik}/{accession_number}) with {len(filing.chunks)}"
        )
        return filing

    def _save(self) -> bool:
        """
        Save the object to cache
        Returns True if saved successfully, False otherwise
        """
        try:
            cache_file_path = f"chunked_filing/{self.cik}/{self.accession_number}.json"
            data = self.model_dump_json()
            return write_obj_to_cache(cache_file_path, data.encode("utf-8"))
        except Exception as e:
            logger.error(f"Failed to save ChunkedFiling to cache: {e}")
            return False
