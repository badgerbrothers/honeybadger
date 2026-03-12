# Code Review: pgvector RAG Integration

**Date:** 2026-03-12
**Reviewer:** Claude
**Scope:** pgvector RAG integration implementation

## Stats

- Files Modified: 9
- Files Added: 18
- New lines: 282
- Deleted lines: 2

## Summary

Code review of pgvector RAG integration. All tests passing (16/16). Found 3 medium-severity issues and 2 low-severity issues.

## Issues Found

### Issue 1
severity: medium
file: worker/rag/embeddings.py
line: 15-19, 26-29
issue: Missing error handling for OpenAI API calls
detail: API calls can fail due to network errors, rate limits, or invalid API keys. No retry logic or error handling present.
suggestion: Add try-except blocks with specific error handling for openai.RateLimitError, openai.APIError, and network errors. Consider implementing exponential backoff retry logic.

### Issue 2
severity: medium
file: backend/app/database.py
line: 30-33
issue: Overly broad exception handling
detail: `except Exception: pass` silently swallows all errors when pgvector extension creation fails, making debugging difficult.
suggestion: Catch specific exceptions (asyncpg.exceptions.FeatureNotSupportedError) and log a warning message instead of silently passing.

### Issue 3
severity: medium
file: worker/rag/indexer.py
line: 88-102
issue: Missing transaction rollback on error
detail: If embedding generation or chunk storage fails partway through, database may be left in inconsistent state.
suggestion: Wrap _store_chunks in try-except and call await self.db_session.rollback() on error.

### Issue 4
severity: low
file: backend/app/config.py
line: 6
issue: Hardcoded database password in default config
detail: While marked as development-only, hardcoded credentials can accidentally leak to production.
suggestion: Consider using empty string as default and require explicit configuration via environment variables.

### Issue 5
severity: low
file: worker/rag/chunker.py
line: 20
issue: Empty text edge case returns single empty chunk
detail: Returning a chunk for empty text may cause unnecessary database writes and API calls.
suggestion: Consider returning empty list for empty text input, or document this behavior clearly.

## Positive Observations

- Clean separation of concerns (embeddings, chunking, indexing, retrieval)
- Comprehensive test coverage (16 tests)
- Type hints used consistently
- Minimal, focused implementations
- Good use of async/await patterns

## Recommendations

1. Add structured logging to all RAG components
2. Implement retry logic for OpenAI API calls
3. Add input validation (max text length, file size limits)
4. Consider adding metrics/monitoring hooks

## Conclusion

Code is production-ready for MVP with minor improvements needed. All identified issues are non-blocking but should be addressed before production deployment.
