# Testing Guidelines

## FastAPI URL Trailing Slash Issue

### Problem

FastAPI automatically redirects POST/PUT/PATCH requests from URLs without trailing slashes to URLs with trailing slashes.

Example:
- Request: `POST /api/projects`
- Response: `307 Temporary Redirect` to `/api/projects/`
- Content: Empty body

This causes test failures when using `httpx.AsyncClient` without proper configuration.

### Solutions

**Option 1: Add trailing slash to URLs** (Recommended)

```python
# ✅ Direct access to endpoint
response = await client.post("/api/projects/", json={"name": "Test"})
```

**Option 2: Enable redirect following**

```python
# ✅ Follow redirects automatically
response = await client.post("/api/projects", json={"name": "Test"}, follow_redirects=True)
```

### Recommendation

**Use Option 1** (trailing slash) for:
- Faster test execution (no redirect overhead)
- Clearer intent
- Direct endpoint testing

**Use Option 2** (follow_redirects) when:
- Testing actual client behavior
- Validating redirect functionality

### Example

```python
@pytest.mark.asyncio
async def test_create_project():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # ✅ Correct: URL with trailing slash
        response = await client.post("/api/projects/", json={"name": "Test Project"})
        assert response.status_code == 201

        # ❌ Wrong: Will get 307 redirect
        # response = await client.post("/api/projects", json={"name": "Test Project"})
```

## Other Testing Best Practices

### Database Cleanup

Tests should be isolated and not depend on execution order. Use fixtures for database setup/teardown.

### Mocking External Services

Always mock external API calls (OpenAI, MinIO, etc.) in unit tests:

```python
with patch("app.services.memory_service.memory_service.summarize_conversation") as mock:
    mock.return_value = "Test summary"
    # ... test code
```

### Coverage Targets

- Aim for 80%+ coverage on new code
- Focus on critical paths and error handling
- Don't test framework code (FastAPI, SQLAlchemy internals)
