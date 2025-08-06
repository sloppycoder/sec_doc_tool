# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

This is a Python project using `uv` for dependency management:

```bash
# Setup virtual environment and install dependencies
uv sync

# Activate virtual environment
source .venv/bin/activate

# Install pre-commit hooks
pre-commit install

# Run linting and auto-fix
ruff check --fix .

# Run type checking
pyright

# Run tests
pytest -v

# Run tests with coverage
pytest --cov=. --cov-report=html
```

## Architecture Overview

This project is a comprehensive SEC EDGAR filing processing tool that downloads, parses, chunks, and analyzes financial documents using NLP techniques.

### Core Components

#### 1. EDGAR Document Processing (`sec_doc_tool/edgar.py`)
- **EdgarFiling class**: Main class for downloading and parsing SEC filings
- Downloads filings from SEC EDGAR database using requests with rate limiting
- Parses index-headers.html and index.html files to extract document metadata
- Handles different document types (485BPOS, HTML, TXT files)
- Implements retry logic with exponential backoff for rate limiting
- Supports filtering by filing catalog with interested CIK lists

#### 2. Document Chunking (`sec_doc_tool/chunking/`)
- **HTML Splitter** (`html_splitter.py`): Splits HTML documents by page breaks
  - Detects various page break markers (HR tags, CSS page-break styles)
  - Preprocesses HTML to remove invisible divs and comments
  - Converts HTML to clean text using html2text
- **Text Chunker** (`text_chunker.py`): Intelligent text segmentation
  - Uses spaCy for sentence boundary detection
  - Handles tables, headers, and structured content
  - Batch processing for performance optimization
  - Configurable chunk size (default: 3000 characters)
- **ChunkedDocument** (`chunking/__init__.py`): Pydantic model for processed documents
  - Automatic persistence and caching of chunked documents
  - Lazy loading from cache to avoid reprocessing
  - Supports both HTML and TXT document types

#### 3. Text Extraction (`sec_doc_tool/text_extractor.py`)
- **TextExtractor class**: Extracts relevant text segments containing fund names
- **Context Detection**: Classifies text as narrative, table, header, list, or parenthetical
- **Sentence/Paragraph Extraction**: Uses spaCy for intelligent text segmentation
- **Quality Scoring**: Calculates quality scores for extracted text segments
- **Multiprocessing Support**: Worker functions for batch processing
- **Caching**: Saves extracted text results to avoid reprocessing

#### 4. Content Analysis & Tagging (`sec_doc_tool/tagging/`)
- **NER Tagger** (`text_tagger.py`): Named Entity Recognition using spaCy
  - Identifies persons, monetary amounts, job titles
  - Counts managers, trustees, and financial ranges
  - Pattern matching for specific financial document entities

#### 5. NLP Model Management (`sec_doc_tool/nlp_model.py`)
- **Lazy Loading**: Global spaCy model instance with fallback support
- **Model Priority**: Prefers en_core_web_lg, falls back to en_core_web_sm
- **Singleton Pattern**: Ensures single model instance per process

#### 6. Caching System (`sec_doc_tool/file_cache.py`)
- **Dual storage support**: Local filesystem and Google Cloud Storage
- **Configurable via environment**: `CACHE_PREFIX` determines storage location
- **Automatic fallback**: GCS → local file → download from source
- **Binary serialization**: Supports various data formats including JSON and pickle

### Data Flow

1. **Input**: CIK (Central Index Key) and Accession Number
2. **Download**: Fetch filing from SEC EDGAR via `EdgarFiling`
3. **Parse**: Extract document content and metadata
4. **Chunk**: Split into manageable segments using HTML splitter or text chunker
5. **Extract**: Use `TextExtractor` to find fund-specific text segments
6. **Tag**: Apply NER analysis using spaCy for entity recognition
7. **Cache**: Store processed results (documents, chunks, extracted texts)
8. **Output**: Structured data models with analyzed content

### Key Technologies

- **Web Scraping**: requests, BeautifulSoup, tenacity (retry logic)
- **NLP**: spaCy (en_core_web_lg/sm), html2text
- **Data Validation**: Pydantic models with JSON serialization
- **Storage**: Google Cloud Storage, local filesystem
- **Testing**: pytest with comprehensive test coverage
- **Multiprocessing**: Support for batch document processing


## Configuration

- `pyproject.toml`: Project dependencies, tool configuration (ruff, pytest, coverage)
- `pyrightconfig.json`: Type checker configuration
- Environment variables loaded from `.env` file via `python-dotenv`
- Logging level controlled by `LOG_LEVEL` environment variable
- Cache storage determined by `CACHE_PREFIX` environment variable


## Claude Code Instructions

Only generate comments for explaining algorithm or situation when the logic is not clear from the code.
Do **NOT** generate comments for every line of code generated.

**Function Organization**: Follow Python convention by placing public functions first, then private functions (prefixed with `_`) at the bottom of the file. This organizes code by visibility and importance.

**IMPORTANT**: When working on this project, Claude Code must ALWAYS follow these steps after making any code changes:

1. **Use pytest for test cases** do not use unittest in this project.

2. **Run Ruff linting and auto-fix** after every code modification:
   ```bash
   ruff check . --fix
   ```

3. **Check for remaining linting issues**:
   ```bash
   ruff check .
   ```

4. **Project-specific linting rules**:
   - Line length limit: **90 characters** (configured in pyproject.toml)
   - Indent width: **4 spaces**
   - Always fix simple issues like line length, imports, spacing automatically
   - Follow PEP8 standards and project conventions

5. **Type checking** (optional but recommended):
   ```bash
   pyright .
   ```

**Never skip the ruff auto-fix step** - it's configured to handle most formatting issues automatically, including line length violations, import sorting, and spacing issues.
