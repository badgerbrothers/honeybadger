# Feature: RAG Document Parsers

The following plan should be complete, but it's important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils types and models. Import from the right files etc.

## Feature Description

Implement document parsers for PDF, Markdown, and TXT files to extract text content for RAG (Retrieval-Augmented Generation) indexing. These parsers will enable the system to process project files and make their content searchable through vector similarity search using pgvector.

The parsers will provide a unified interface for extracting clean text from different document formats, handling encoding issues, and providing structured output suitable for chunking and embedding generation.

## User Story

As a Badgers platform user
I want the system to automatically parse and index my project documents (PDF, Markdown, TXT)
So that the AI agent can retrieve relevant context from my files when executing tasks

## Problem Statement

The RAG system needs to extract text content from various document formats stored in user projects. Without proper parsers, the system cannot:
- Index document content for vector search
- Provide relevant context to agents during task execution
- Support document analysis tasks
- Enable semantic search across project files

## Solution Statement

Create a modular parser system with:
1. **Base Parser Interface**: Abstract class defining common parsing contract
2. **Format-Specific Parsers**: Concrete implementations for PDF, Markdown, and TXT
3. **Error Handling**: Custom exceptions for parsing failures
4. **Metadata Extraction**: Capture document metadata (page count, encoding, etc.)
5. **Text Normalization**: Clean and normalize extracted text for embedding

## Feature Metadata

**Feature Type**: New Capability
**Estimated Complexity**: Medium
**Primary Systems Affected**: worker/rag module
**Dependencies**: pypdf (already installed), python-markdown (to be added)

---

## CONTEXT REFERENCES

### Relevant Codebase Files IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

- `worker/sandbox/exceptions.py` (lines 1-22) - Why: Exception pattern to mirror for parser exceptions
- `worker/tests/test_docker_backend.py` (lines 1-93) - Why: Testing pattern with pytest and mocking
- `worker/pyproject.toml` (lines 1-28) - Why: Dependency management pattern, pypdf already available
- `backend/app/models/base.py` (lines 1-14) - Why: Base class pattern (though not directly applicable, shows project style)

### New Files to Create

- `worker/rag/parsers/base.py` - Abstract base parser class and common utilities
- `worker/rag/parsers/pdf_parser.py` - PDF document parser using pypdf
- `worker/rag/parsers/markdown_parser.py` - Markdown document parser
- `worker/rag/parsers/txt_parser.py` - Plain text document parser
- `worker/rag/parsers/exceptions.py` - Custom exceptions for parsing errors
- `worker/rag/parsers/__init__.py` - Public API exports
- `worker/tests/test_pdf_parser.py` - Unit tests for PDF parser
- `worker/tests/test_markdown_parser.py` - Unit tests for Markdown parser
- `worker/tests/test_txt_parser.py` - Unit tests for TXT parser
- `worker/tests/fixtures/sample.pdf` - Test fixture PDF file
- `worker/tests/fixtures/sample.md` - Test fixture Markdown file
- `worker/tests/fixtures/sample.txt` - Test fixture text file

### Relevant Documentation YOU SHOULD READ THESE BEFORE IMPLEMENTING!

- [pypdf Documentation](https://pypdf.readthedocs.io/en/stable/)
  - Specific section: Text Extraction
  - Why: Already installed, need to understand PdfReader API and text extraction methods
- [Python Markdown Documentation](https://python-markdown.github.io/)
  - Specific section: Basic Usage
  - Why: For parsing Markdown to extract plain text
- [Python pathlib Documentation](https://docs.python.org/3/library/pathlib.html)
  - Specific section: Path operations
  - Why: For file handling and path validation

### Patterns to Follow

**Exception Pattern** (from `worker/sandbox/exceptions.py`):
```python
class BaseError(Exception):
    """Base exception."""
    pass

class SpecificError(BaseError):
    """Specific error case."""
    pass
```

**Testing Pattern** (from `worker/tests/test_docker_backend.py`):
```python
import pytest
from unittest.mock import Mock, patch

def test_success_case():
    """Test successful operation."""
    # Arrange
    # Act
    # Assert

@patch('module.dependency')
def test_with_mock(mock_dep):
    """Test with mocked dependency."""
    mock_dep.return_value = expected_value
    # test logic
```

**Naming Conventions:**
- snake_case for functions, variables, modules
- PascalCase for classes
- Descriptive test names: `test_<action>_<condition>`
- Docstrings for all public classes and methods

**Error Handling:**
- Custom exceptions inherit from base exception
- Raise specific exceptions for different failure modes
- Include descriptive error messages

**Module Structure:**
- `__init__.py` exports public API
- Private helpers prefixed with underscore
- Clear separation of concerns

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation

Set up base parser infrastructure and exception handling.

**Tasks:**
- Create custom exception classes for parsing errors
- Define abstract base parser class with common interface
- Set up parser registry/factory pattern (optional, for extensibility)

### Phase 2: Core Implementation

Implement concrete parsers for each document format.

**Tasks:**
- Implement PDF parser using pypdf library
- Implement Markdown parser (extract text, strip formatting)
- Implement TXT parser with encoding detection
- Add metadata extraction for each format

### Phase 3: Integration

Update module exports and ensure parsers are accessible.

**Tasks:**
- Update `worker/rag/parsers/__init__.py` with public API
- Create parser factory/registry if needed
- Ensure clean import paths

### Phase 4: Testing & Validation

Comprehensive testing for all parsers.

**Tasks:**
- Create test fixtures (sample documents)
- Implement unit tests for each parser
- Test edge cases (empty files, corrupted files, encoding issues)
- Validate text extraction quality

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### Task 1: CREATE worker/rag/parsers/exceptions.py

- **IMPLEMENT**: Custom exception classes for parsing errors
- **PATTERN**: Mirror `worker/sandbox/exceptions.py` (lines 1-22)
- **IMPORTS**: None (base Exception only)
- **CLASSES**:
  - `ParserError(Exception)` - Base parser exception
  - `UnsupportedFormatError(ParserError)` - Unsupported file format
  - `ParseError(ParserError)` - Failed to parse document
  - `FileReadError(ParserError)` - Failed to read file
- **VALIDATE**: `cd worker && python -c "from rag.parsers.exceptions import ParserError, ParseError; print('OK')"`

### Task 2: CREATE worker/rag/parsers/base.py

- **IMPLEMENT**: Abstract base parser class with common interface
- **PATTERN**: ABC pattern with abstractmethod
- **IMPORTS**: `from abc import ABC, abstractmethod`, `from pathlib import Path`, `from typing import Dict, Any`
- **CLASS**: `BaseParser(ABC)` with:
  - `@abstractmethod parse(file_path: Path) -> Dict[str, Any]` - Returns {"text": str, "metadata": dict}
  - `@abstractmethod supported_extensions() -> list[str]` - Returns list of supported file extensions
  - Helper method `_validate_file(file_path: Path)` - Check file exists and readable
- **GOTCHA**: Use Path for file handling, not strings
- **VALIDATE**: `cd worker && python -c "from rag.parsers.base import BaseParser; print('OK')"`

### Task 3: ADD python-markdown dependency

- **IMPLEMENT**: Add markdown library to pyproject.toml
- **PATTERN**: Follow existing dependency format in `worker/pyproject.toml` (lines 6-21)
- **UPDATE**: Add `"markdown>=3.5.0",` to dependencies list
- **VALIDATE**: `cd worker && uv sync && uv pip list | grep markdown`

### Task 4: CREATE worker/rag/parsers/txt_parser.py

- **IMPLEMENT**: Plain text parser with encoding detection
- **PATTERN**: Inherit from BaseParser
- **IMPORTS**: `from pathlib import Path`, `from typing import Dict, Any`, `from .base import BaseParser`, `from .exceptions import ParseError, FileReadError`
- **CLASS**: `TxtParser(BaseParser)` with:
  - `parse(file_path: Path)` - Read file with UTF-8, fallback to latin-1
  - `supported_extensions()` - Returns [".txt"]
  - Extract metadata: file size, line count, encoding used
- **GOTCHA**: Handle encoding errors gracefully, try UTF-8 first then latin-1
- **VALIDATE**: `cd worker && python -c "from rag.parsers.txt_parser import TxtParser; p = TxtParser(); print('OK')"`

### Task 5: CREATE worker/rag/parsers/markdown_parser.py

- **IMPLEMENT**: Markdown parser that extracts plain text
- **PATTERN**: Inherit from BaseParser
- **IMPORTS**: `import markdown`, `from pathlib import Path`, `from typing import Dict, Any`, `import re`, `from .base import BaseParser`, `from .exceptions import ParseError, FileReadError`
- **CLASS**: `MarkdownParser(BaseParser)` with:
  - `parse(file_path: Path)` - Read markdown, convert to HTML, strip tags to get plain text
  - `supported_extensions()` - Returns [".md", ".markdown"]
  - `_strip_html_tags(html: str) -> str` - Remove HTML tags using regex
  - Extract metadata: heading count, word count
- **GOTCHA**: Use `markdown.markdown()` to convert, then strip HTML tags with `re.sub(r'<[^>]+>', '', html)`
- **VALIDATE**: `cd worker && python -c "from rag.parsers.markdown_parser import MarkdownParser; p = MarkdownParser(); print('OK')"`

### Task 6: CREATE worker/rag/parsers/pdf_parser.py

- **IMPLEMENT**: PDF parser using pypdf library
- **PATTERN**: Inherit from BaseParser
- **IMPORTS**: `from pypdf import PdfReader`, `from pathlib import Path`, `from typing import Dict, Any`, `from .base import BaseParser`, `from .exceptions import ParseError, FileReadError`
- **CLASS**: `PdfParser(BaseParser)` with:
  - `parse(file_path: Path)` - Extract text from all pages using PdfReader
  - `supported_extensions()` - Returns [".pdf"]
  - Extract metadata: page count, author, title (from PDF metadata)
  - Concatenate text from all pages with page separators
- **GOTCHA**: pypdf uses `PdfReader(file_path)` then iterate `reader.pages` and call `page.extract_text()`
- **VALIDATE**: `cd worker && python -c "from rag.parsers.pdf_parser import PdfParser; p = PdfParser(); print('OK')"`

### Task 7: UPDATE worker/rag/parsers/__init__.py

- **IMPLEMENT**: Export public API for parsers
- **PATTERN**: Follow `backend/app/models/__init__.py` export pattern
- **IMPORTS**: Import all parsers and exceptions
- **EXPORTS**: `__all__` list with BaseParser, all concrete parsers, all exceptions
- **VALIDATE**: `cd worker && python -c "from rag.parsers import PdfParser, MarkdownParser, TxtParser; print('OK')"`

### Task 8: CREATE worker/tests/fixtures/sample.txt

- **IMPLEMENT**: Create test fixture text file
- **CONTENT**: Multi-line text with UTF-8 characters
- **EXAMPLE**:
```
Hello World!
This is a test document.
It contains multiple lines.
Special chars: café, naïve, 你好
```
- **VALIDATE**: `test -f worker/tests/fixtures/sample.txt && echo OK`

### Task 9: CREATE worker/tests/fixtures/sample.md

- **IMPLEMENT**: Create test fixture Markdown file
- **CONTENT**: Markdown with headers, lists, links, code blocks
- **EXAMPLE**:
```markdown
# Test Document

This is a **test** document with *formatting*.

## Features
- Item 1
- Item 2

[Link](https://example.com)

`code snippet`
```
- **VALIDATE**: `test -f worker/tests/fixtures/sample.md && echo OK`

### Task 10: CREATE worker/tests/fixtures/sample.pdf

- **IMPLEMENT**: Create minimal test PDF file
- **APPROACH**: Use Python script to generate PDF with pypdf or reportlab
- **CONTENT**: Simple single-page PDF with "Test PDF Document" text
- **SCRIPT**: Create helper script `worker/tests/create_test_pdf.py` that generates the PDF
- **VALIDATE**: `cd worker && python tests/create_test_pdf.py && test -f tests/fixtures/sample.pdf && echo OK`

### Task 11: CREATE worker/tests/test_txt_parser.py

- **IMPLEMENT**: Unit tests for TxtParser
- **PATTERN**: Mirror `worker/tests/test_docker_backend.py` structure
- **IMPORTS**: `pytest`, `from pathlib import Path`, `from rag.parsers.txt_parser import TxtParser`, `from rag.parsers.exceptions import FileReadError`
- **TESTS**:
  - `test_parse_success()` - Parse sample.txt successfully
  - `test_parse_returns_text_and_metadata()` - Verify return structure
  - `test_parse_nonexistent_file()` - Raises FileReadError
  - `test_supported_extensions()` - Returns [".txt"]
- **VALIDATE**: `cd worker && uv run pytest tests/test_txt_parser.py -v`

### Task 12: CREATE worker/tests/test_markdown_parser.py

- **IMPLEMENT**: Unit tests for MarkdownParser
- **PATTERN**: Mirror test_txt_parser.py structure
- **IMPORTS**: `pytest`, `from pathlib import Path`, `from rag.parsers.markdown_parser import MarkdownParser`, `from rag.parsers.exceptions import FileReadError`
- **TESTS**:
  - `test_parse_success()` - Parse sample.md successfully
  - `test_parse_strips_formatting()` - Verify HTML tags removed
  - `test_parse_returns_metadata()` - Check metadata structure
  - `test_parse_nonexistent_file()` - Raises FileReadError
  - `test_supported_extensions()` - Returns [".md", ".markdown"]
- **VALIDATE**: `cd worker && uv run pytest tests/test_markdown_parser.py -v`

### Task 13: CREATE worker/tests/test_pdf_parser.py

- **IMPLEMENT**: Unit tests for PdfParser
- **PATTERN**: Mirror test_txt_parser.py structure
- **IMPORTS**: `pytest`, `from pathlib import Path`, `from rag.parsers.pdf_parser import PdfParser`, `from rag.parsers.exceptions import FileReadError, ParseError`
- **TESTS**:
  - `test_parse_success()` - Parse sample.pdf successfully
  - `test_parse_returns_text_and_metadata()` - Verify structure with page_count
  - `test_parse_nonexistent_file()` - Raises FileReadError
  - `test_parse_corrupted_pdf()` - Raises ParseError (use invalid file)
  - `test_supported_extensions()` - Returns [".pdf"]
- **VALIDATE**: `cd worker && uv run pytest tests/test_pdf_parser.py -v`

### Task 14: CREATE worker/tests/test_base_parser.py

- **IMPLEMENT**: Unit tests for BaseParser abstract class
- **PATTERN**: Test abstract class behavior
- **IMPORTS**: `pytest`, `from pathlib import Path`, `from rag.parsers.base import BaseParser`
- **TESTS**:
  - `test_cannot_instantiate_base_parser()` - Verify ABC prevents instantiation
  - `test_validate_file_exists()` - Test file validation helper
  - `test_validate_file_not_found()` - Test validation raises error
- **VALIDATE**: `cd worker && uv run pytest tests/test_base_parser.py -v`

---

## TESTING STRATEGY

### Unit Tests

**Framework**: pytest with pytest-asyncio (already configured)

**Coverage Requirements**: 80%+ line coverage for all parser modules

**Test Structure**:
- Arrange-Act-Assert pattern
- One test per behavior/edge case
- Descriptive test names: `test_<action>_<condition>`
- Use fixtures for sample files
- Mock external dependencies if needed

**Test Categories**:
1. **Happy Path**: Successful parsing with valid files
2. **Error Cases**: Invalid files, missing files, corrupted content
3. **Edge Cases**: Empty files, large files, special characters
4. **Metadata**: Verify metadata extraction accuracy

### Integration Tests

**Scope**: Not required for MVP - parsers are independent units

**Future Consideration**: Test parser integration with RAG indexer when implemented

### Edge Cases

1. **Empty Files**: All parsers should handle empty files gracefully
2. **Large Files**: Test with multi-MB files (performance consideration)
3. **Encoding Issues**: TXT parser with various encodings (UTF-8, latin-1, UTF-16)
4. **Corrupted Files**: PDF parser with invalid PDF structure
5. **Special Characters**: Unicode, emojis, non-ASCII characters
6. **Missing Extensions**: Files without extensions
7. **Symlinks**: Files accessed via symbolic links

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature correctness.

### Level 1: Syntax & Style

```bash
cd worker && uv run ruff check rag/parsers/
```

### Level 2: Unit Tests

```bash
cd worker && uv run pytest tests/test_txt_parser.py tests/test_markdown_parser.py tests/test_pdf_parser.py tests/test_base_parser.py -v
```

### Level 3: Integration Tests

```bash
# Run all parser tests together
cd worker && uv run pytest tests/test_*_parser.py -v
```

### Level 4: Manual Validation

```bash
# Test each parser manually with fixtures
cd worker && python -c "
from pathlib import Path
from rag.parsers import TxtParser, MarkdownParser, PdfParser

# Test TXT
txt_parser = TxtParser()
result = txt_parser.parse(Path('tests/fixtures/sample.txt'))
print(f'TXT: {len(result[\"text\"])} chars')

# Test Markdown
md_parser = MarkdownParser()
result = md_parser.parse(Path('tests/fixtures/sample.md'))
print(f'MD: {len(result[\"text\"])} chars')

# Test PDF
pdf_parser = PdfParser()
result = pdf_parser.parse(Path('tests/fixtures/sample.pdf'))
print(f'PDF: {len(result[\"text\"])} chars, {result[\"metadata\"][\"page_count\"]} pages')
"
```

### Level 5: Coverage Check

```bash
cd worker && uv run pytest tests/test_*_parser.py --cov=rag.parsers --cov-report=term-missing
```

---

## ACCEPTANCE CRITERIA

- [ ] TxtParser successfully extracts text from .txt files with UTF-8 and latin-1 encoding
- [ ] MarkdownParser extracts plain text from .md files, stripping all formatting
- [ ] PdfParser extracts text from .pdf files and returns page count metadata
- [ ] All parsers implement BaseParser interface consistently
- [ ] All parsers return structured output: `{"text": str, "metadata": dict}`
- [ ] Custom exceptions (ParserError, ParseError, FileReadError) properly raised
- [ ] All validation commands pass with zero errors
- [ ] Unit test coverage ≥80% for all parser modules
- [ ] All tests pass (txt, markdown, pdf, base parser tests)
- [ ] Code follows project conventions (snake_case, docstrings, type hints)
- [ ] No regressions in existing functionality
- [ ] Parsers handle edge cases gracefully (empty files, missing files, encoding issues)

---

## COMPLETION CHECKLIST

- [ ] All 14 tasks completed in order
- [ ] Each task validation passed immediately after implementation
- [ ] All validation commands executed successfully
- [ ] Full test suite passes (all parser tests)
- [ ] Ruff linting passes with zero errors
- [ ] Manual testing confirms all parsers work correctly
- [ ] Test fixtures created and committed
- [ ] All acceptance criteria met
- [ ] Code reviewed for quality and maintainability
- [ ] No TODO or FIXME comments left in code

---

## NOTES

### Design Decisions

**1. Abstract Base Class Pattern**
- Chose ABC pattern for BaseParser to enforce consistent interface across all parsers
- Ensures all parsers implement `parse()` and `supported_extensions()` methods
- Provides common validation logic in base class

**2. Return Structure**
- Standardized return format: `{"text": str, "metadata": dict}`
- Allows extensibility - different parsers can add format-specific metadata
- Consistent interface simplifies RAG indexer integration

**3. Error Handling Strategy**
- Custom exception hierarchy (ParserError base, specific subclasses)
- Mirrors existing sandbox exception pattern for consistency
- Enables granular error handling in calling code

**4. Encoding Handling**
- TXT parser tries UTF-8 first, falls back to latin-1
- Covers 99% of real-world text files
- Could extend with chardet library if needed (not in MVP)

**5. Markdown Processing**
- Convert to HTML first, then strip tags
- Simpler than parsing Markdown AST directly
- Preserves text content while removing formatting

**6. PDF Text Extraction**
- Use pypdf (already installed) instead of heavier alternatives (pdfminer, PyMuPDF)
- Good enough for MVP, can upgrade if quality issues arise
- Concatenate pages with separators for context preservation

### Trade-offs

**Simplicity vs Features**
- Chose simple text extraction over advanced features (OCR, table extraction, image text)
- MVP focuses on basic text content for RAG indexing
- Can extend later if needed

**Performance vs Accuracy**
- No optimization for large files in MVP
- Acceptable for typical project documents (<10MB)
- Can add streaming/chunking if performance issues arise

**Dependencies**
- Minimal new dependencies (only python-markdown added)
- Leverages existing pypdf installation
- Reduces maintenance burden

### Future Enhancements

1. **Advanced PDF Features**: Table extraction, OCR for scanned PDFs
2. **More Formats**: DOCX, HTML, RTF, CSV
3. **Streaming**: Handle large files without loading entirely into memory
4. **Encoding Detection**: Use chardet for automatic encoding detection
5. **Metadata Enrichment**: Extract more document metadata (author, dates, keywords)
6. **Text Cleaning**: Advanced normalization (remove headers/footers, deduplicate)
7. **Language Detection**: Identify document language for better embedding

### Integration Notes

**RAG Indexer Integration** (Future):
- Parsers output plain text ready for chunking
- Metadata can be stored alongside embeddings in pgvector
- File path should be tracked for source attribution
- Consider chunking strategy: fixed-size vs semantic (paragraph/section)

**API Integration** (Future):
- Could expose parsers via API endpoint for on-demand parsing
- Useful for preview/validation before indexing
- Consider async processing for large files

### Testing Notes

- Test fixtures are minimal for fast test execution
- Real-world testing should include larger, more complex documents
- Consider adding performance benchmarks for large files
- Edge case testing is critical (corrupted files, unusual encodings)

### Security Considerations

- File path validation prevents directory traversal attacks
- No arbitrary code execution (unlike some document parsers)
- Consider file size limits to prevent DoS via large files
- Validate file extensions match actual content (magic number check)

### Performance Expectations

- TXT: <10ms for typical files (<1MB)
- Markdown: <50ms for typical files (<1MB)
- PDF: <500ms for typical files (<10MB, <100 pages)
- Memory usage: ~2-3x file size during parsing

---

## CONFIDENCE SCORE

**8/10** - High confidence for one-pass implementation success

**Reasoning:**
- Clear requirements and well-defined scope
- Existing patterns to follow (exceptions, testing)
- Dependencies already available (pypdf) or simple to add (markdown)
- Straightforward implementation with minimal complexity
- Comprehensive task breakdown with validation at each step

**Risk Factors:**
- PDF text extraction quality varies by PDF type (could need iteration)
- Encoding edge cases in TXT parser might need refinement
- Test fixture creation (especially PDF) might need manual adjustment

**Mitigation:**
- Each task has immediate validation command
- Test-driven approach catches issues early
- Simple implementations can be refined based on real-world usage
