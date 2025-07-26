from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

from sec_doc_tool.chunking.html_splitter import split_html_by_pagebreak
from sec_doc_tool.chunking.text_chunker import chunk_text, trim_html
from sec_doc_tool.edgar import EdgarFiling
from sec_doc_tool.file_cache import load_obj_from_cache, write_obj_to_cache

logger = logging.getLogger(__name__)


class ChunkedDocument(BaseModel):
    """
    Represents a filing that has been split into chunks
    """

    cik: str
    accession_number: str
    date_filed: str
    html_pages: list[str] = []
    text_chunks: list[str] = []
    text_chunk_refs: list[int] = Field(default_factory=list)
    chunk_tags: list[dict[str, Any]] = Field(default_factory=list)

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
                    f"Loaded ChunkedFiling({cik}/{accession_number}) with {len(obj.text_chunks)} chunks from cache"
                )
                return obj

        edgar_filing = EdgarFiling(cik=cik, accession_number=accession_number)
        doc_contents = edgar_filing.get_doc_content("485BPOS", file_types=["htm", "txt"])
        if not doc_contents:
            logger.info("No HTML or TXT content found for {cik}/{accession_number}")
            return None

        doc_path, doc_content = doc_contents[0]

        if doc_path.endswith(".htm"):
            html_pages = split_html_by_pagebreak(doc_content)
            text_chunks = []
            page_refs = []
            for i, page in enumerate(html_pages):
                chunks = chunk_text(trim_html(page))
                text_chunks.extend(chunks)
                page_refs.append(i)

        elif doc_path.endswith(".txt"):
            html_pages = []
            page_refs = []
            text_chunks = chunk_text(doc_content)
        else:
            raise ValueError(f"Unsupported document type: {doc_path}")

        # text_chunks = add_context_from_neighbors(text_chunks)

        filing = ChunkedDocument(
            cik=cik,
            accession_number=accession_number,
            date_filed=edgar_filing.date_filed,
            html_pages=html_pages,
            text_chunks=text_chunks,
            text_chunk_refs=page_refs,
        )
        # save the chunked filing to cache
        if filing._save():
            logger.debug(
                f"Created new ChunkedFiling({cik}/{accession_number}) with {len(filing.text_chunks)}"
            )
        else:
            logger.warning(
                f"Failed to save ChunkedFiling({cik}/{accession_number}) to cache"
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
