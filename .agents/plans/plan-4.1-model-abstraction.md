# Feature: Unified Model Abstraction Layer

The following plan should be complete, but it's important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils types and models. Import from the right files etc.

## Feature Description

Create a unified model abstraction layer that provides a consistent interface for interacting with both OpenAI-compatible APIs and Anthropic's Claude API. This abstraction enables the agent orchestrator to switch between different LLM providers seamlessly without changing business logic, supporting multi-provider strategies, fallback mechanisms, and cost optimization.

## User Story

As a **system architect**
I want to **abstract LLM provider implementations behind a unified interface**
So that **the orchestrator can use different models (OpenAI, Anthropic) interchangeably without code changes**

## Problem Statement

The Badgers MVP needs to support multiple LLM providers (OpenAI-compatible APIs and Anthropic) for agent orchestration. Currently, there's no abstraction layer, which would lead to:
- Tight coupling between orchestrator logic and specific provider SDKs
- Difficulty switching providers or implementing fallback strategies
- Code duplication when supporting multiple providers
- Hard-to-test orchestrator logic due to direct SDK dependencies

## Solution Statement

Implement a provider-agnostic model abstraction layer with:
1. **Unified Interface**: Common protocol/abstract base class for all providers
2. **Provider Implementations**: Concrete classes for OpenAI and Anthropic
3. **Factory Pattern**: Model provider factory for instantiation
4. **Configuration**: Environment-based provider selection and API key management
5. **Streaming Support**: Unified streaming interface for real-time responses
6. **Error Handling**: Consistent error types across providers

## Feature Metadata

**Feature Type**: New Capability
**Estimated Complexity**: Medium
**Primary Systems Affected**: worker/models, worker/orchestrator, worker configuration
**Dependencies**: openai>=1.10.0, anthropic>=0.18.0, pydantic>=2.0.0, structlog>=24.1.0

---

## CONTEXT REFERENCES

### Relevant Codebase Files IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

- `backend/app/config.py` (lines 1-12) - Why: Configuration pattern using pydantic_settings.BaseSettings
- `backend/app/schemas/task.py` (lines 1-44) - Why: Pydantic schema patterns with Field validation
- `backend/tests/conftest.py` (lines 1-18) - Why: Test fixture patterns for async tests
- `worker/pyproject.toml` (lines 1-28) - Why: Dependencies and project structure

### New Files to Create

- `worker/models/base.py` - Abstract base class and protocol definitions
- `worker/models/openai_provider.py` - OpenAI provider implementation
- `worker/models/anthropic_provider.py` - Anthropic provider implementation
- `worker/models/factory.py` - Model provider factory
- `worker/models/types.py` - Shared types and enums
- `worker/models/exceptions.py` - Model-specific exceptions
- `worker/config.py` - Worker configuration management
- `tests/test_models_base.py` - Base model tests
- `tests/test_models_openai.py` - OpenAI provider tests
- `tests/test_models_anthropic.py` - Anthropic provider tests
- `tests/test_models_factory.py` - Factory tests

### Relevant Documentation YOU SHOULD READ THESE BEFORE IMPLEMENTING!

- [OpenAI Python SDK](https://github.com/openai/openai-python#usage)
  - Specific section: Chat Completions API
  - Why: Required for implementing OpenAI provider with correct API patterns
- [Anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python#usage)
  - Specific section: Messages API and Streaming
  - Why: Required for implementing Anthropic provider with correct API patterns
- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
  - Specific section: Environment variable loading
  - Why: Configuration management pattern
- [Python ABC Module](https://docs.python.org/3/library/abc.html)
  - Specific section: Abstract Base Classes
  - Why: Creating provider interface

### Patterns to Follow

**Naming Conventions:**
```python
# Classes: PascalCase
class ModelProvider(ABC):
    pass

# Functions/methods: snake_case
async def generate_completion(self, messages: list) -> str:
    pass

# Constants: UPPER_SNAKE_CASE
DEFAULT_MODEL = "gpt-4"
```

**Configuration Pattern:**
```python
# From backend/app/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql://..."

    class Config:
        env_file = ".env"

settings = Settings()
```

**Pydantic Schema Pattern:**
```python
# From backend/app/schemas/task.py
from pydantic import BaseModel, Field

class TaskCreate(BaseModel):
    goal: str = Field(..., min_length=1)
    skill: str | None = Field(None, max_length=100)
```

**Async Test Pattern:**
```python
# From backend/tests/conftest.py
import pytest
import asyncio

@pytest.fixture(scope="function")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
```

**Logging Pattern:**
```python
# Project uses structlog
import structlog
logger = structlog.get_logger(__name__)
logger.info("event_name", key="value")
```

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation

Set up base structures, types, and configuration before implementing provider-specific logic.

**Tasks:**
- Define shared types (Message, ModelConfig, CompletionResponse)
- Create abstract base class for model providers
- Set up configuration management for API keys and model selection
- Define custom exceptions for model operations

### Phase 2: Core Implementation

Implement concrete provider classes for OpenAI and Anthropic.

**Tasks:**
- Implement OpenAI provider with chat completions
- Implement Anthropic provider with messages API
- Add streaming support for both providers
- Implement provider factory for instantiation

### Phase 3: Integration

Connect the model abstraction to the worker configuration system.

**Tasks:**
- Update worker configuration to include model settings
- Create factory initialization in worker startup
- Add logging and error handling
- Document usage patterns

### Phase 4: Testing & Validation

Comprehensive testing of all components.

**Tasks:**
- Unit tests for each provider with mocked SDK calls
- Integration tests with factory
- Error handling and edge case tests
- Validate against acceptance criteria

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### CREATE worker/models/types.py

- **IMPLEMENT**: Shared types and enums for model abstraction
- **PATTERN**: Pydantic BaseModel from backend/app/schemas/task.py:1-44
- **IMPORTS**: `from pydantic import BaseModel, Field; from enum import Enum; from typing import Literal`
- **GOTCHA**: Use Pydantic v2 syntax (model_config instead of Config class)
- **VALIDATE**: `cd worker && uv run python -c "from models.types import ModelProvider, Message, CompletionResponse; print('Types imported successfully')"`

**Implementation details:**
```python
# Define ModelProvider enum (openai, anthropic)
# Define Message dataclass (role, content)
# Define ModelConfig (temperature, max_tokens, etc.)
# Define CompletionResponse (content, usage, model)
# Define StreamChunk for streaming responses
```

### CREATE worker/models/exceptions.py

- **IMPLEMENT**: Custom exceptions for model operations
- **PATTERN**: Standard Python exception hierarchy
- **IMPORTS**: `from typing import Any`
- **GOTCHA**: Include provider name and original error in exception context
- **VALIDATE**: `cd worker && uv run python -c "from models.exceptions import ModelError, ProviderError; print('Exceptions imported')"`

**Implementation details:**
```python
# ModelError (base exception)
# ProviderError (provider-specific errors)
# ConfigurationError (missing API keys, invalid config)
# RateLimitError (rate limiting)
# InvalidRequestError (bad requests)
```

### CREATE worker/models/base.py

- **IMPLEMENT**: Abstract base class defining the model provider interface
- **PATTERN**: Python ABC from standard library
- **IMPORTS**: `from abc import ABC, abstractmethod; from typing import AsyncIterator; from models.types import Message, CompletionResponse, ModelConfig, StreamChunk`
- **GOTCHA**: All methods must be async to support async orchestrator
- **VALIDATE**: `cd worker && uv run python -c "from models.base import ModelProvider; print('Base class imported')"`

**Implementation details:**
```python
# Abstract ModelProvider class with:
# - __init__(api_key: str, model: str, config: ModelConfig)
# - async generate(messages: list[Message]) -> CompletionResponse
# - async stream(messages: list[Message]) -> AsyncIterator[StreamChunk]
# - validate_config() -> None
```

### CREATE worker/config.py

- **IMPLEMENT**: Worker configuration using pydantic_settings
- **PATTERN**: backend/app/config.py:1-12
- **IMPORTS**: `from pydantic_settings import BaseSettings; from models.types import ModelProvider`
- **GOTCHA**: Use env_file = ".env" for local development
- **VALIDATE**: `cd worker && uv run python -c "from config import settings; print(f'Config loaded: {settings.model_provider}')"`

**Implementation details:**
```python
# Settings class with:
# - model_provider: ModelProvider (default: openai)
# - openai_api_key: str | None
# - anthropic_api_key: str | None
# - default_model: str (default: gpt-4)
# - temperature: float (default: 0.7)
# - max_tokens: int (default: 2000)
```

### CREATE worker/models/openai_provider.py

- **IMPLEMENT**: OpenAI provider implementation
- **PATTERN**: models/base.py ModelProvider interface
- **IMPORTS**: `from openai import AsyncOpenAI; from models.base import ModelProvider; from models.types import Message, CompletionResponse, StreamChunk; from models.exceptions import ProviderError; import structlog`
- **GOTCHA**: OpenAI uses "system", "user", "assistant" roles; handle streaming with async for
- **VALIDATE**: `cd worker && uv run python -c "from models.openai_provider import OpenAIProvider; print('OpenAI provider imported')"`

**Implementation details:**
```python
# OpenAIProvider class:
# - Initialize AsyncOpenAI client
# - Implement generate() using client.chat.completions.create()
# - Implement stream() using client.chat.completions.create(stream=True)
# - Convert Message format to OpenAI format
# - Handle errors and wrap in ProviderError
# - Log all API calls with structlog
```

### CREATE worker/models/anthropic_provider.py

- **IMPLEMENT**: Anthropic provider implementation
- **PATTERN**: models/base.py ModelProvider interface
- **IMPORTS**: `from anthropic import AsyncAnthropic; from models.base import ModelProvider; from models.types import Message, CompletionResponse, StreamChunk; from models.exceptions import ProviderError; import structlog`
- **GOTCHA**: Anthropic requires system message separate from messages list; use client.messages.create()
- **VALIDATE**: `cd worker && uv run python -c "from models.anthropic_provider import AnthropicProvider; print('Anthropic provider imported')"`

**Implementation details:**
```python
# AnthropicProvider class:
# - Initialize AsyncAnthropic client
# - Implement generate() using client.messages.create()
# - Implement stream() using client.messages.stream()
# - Separate system message from messages list
# - Convert Message format to Anthropic format
# - Handle errors and wrap in ProviderError
# - Log all API calls with structlog
```

### CREATE worker/models/factory.py

- **IMPLEMENT**: Factory for creating model provider instances
- **PATTERN**: Factory pattern with type-based instantiation
- **IMPORTS**: `from models.base import ModelProvider; from models.openai_provider import OpenAIProvider; from models.anthropic_provider import AnthropicProvider; from models.types import ModelProvider as ProviderEnum, ModelConfig; from models.exceptions import ConfigurationError; from config import settings`
- **GOTCHA**: Validate API keys before instantiation
- **VALIDATE**: `cd worker && uv run python -c "from models.factory import create_model_provider; print('Factory imported')"`

**Implementation details:**
```python
# create_model_provider() function:
# - Accept provider: ProviderEnum, model: str | None, config: ModelConfig | None
# - Use settings for defaults
# - Validate API key exists for selected provider
# - Return appropriate provider instance
# - Raise ConfigurationError if invalid
```

### UPDATE worker/models/__init__.py

- **IMPLEMENT**: Export public API from models package
- **PATTERN**: Standard Python package __init__.py
- **IMPORTS**: All public classes and functions from submodules
- **GOTCHA**: Only export what orchestrator needs
- **VALIDATE**: `cd worker && uv run python -c "from models import create_model_provider, ModelProvider, Message; print('Package imports work')"`

**Implementation details:**
```python
# Export:
# - create_model_provider (factory function)
# - ModelProvider (enum)
# - Message, CompletionResponse, ModelConfig (types)
# - ModelError and subclasses (exceptions)
```

### CREATE worker/tests/test_models_base.py

- **IMPLEMENT**: Tests for base types and exceptions
- **PATTERN**: backend/tests/conftest.py:1-18 for async fixtures
- **IMPORTS**: `import pytest; from models.types import Message, ModelConfig, CompletionResponse; from models.exceptions import ModelError`
- **GOTCHA**: Test Pydantic validation rules
- **VALIDATE**: `cd worker && uv run pytest tests/test_models_base.py -v`

**Implementation details:**
```python
# Test Message validation (role, content)
# Test ModelConfig defaults and validation
# Test CompletionResponse structure
# Test exception hierarchy
```

### CREATE worker/tests/test_models_openai.py

- **IMPLEMENT**: Tests for OpenAI provider with mocked SDK
- **PATTERN**: pytest-asyncio for async tests
- **IMPORTS**: `import pytest; from unittest.mock import AsyncMock, patch; from models.openai_provider import OpenAIProvider`
- **GOTCHA**: Mock AsyncOpenAI client, not actual API calls
- **VALIDATE**: `cd worker && uv run pytest tests/test_models_openai.py -v`

**Implementation details:**
```python
# Test generate() with mocked response
# Test stream() with mocked async iterator
# Test error handling (API errors, rate limits)
# Test message format conversion
```

### CREATE worker/tests/test_models_anthropic.py

- **IMPLEMENT**: Tests for Anthropic provider with mocked SDK
- **PATTERN**: pytest-asyncio for async tests
- **IMPORTS**: `import pytest; from unittest.mock import AsyncMock, patch; from models.anthropic_provider import AnthropicProvider`
- **GOTCHA**: Mock AsyncAnthropic client, test system message separation
- **VALIDATE**: `cd worker && uv run pytest tests/test_models_anthropic.py -v`

**Implementation details:**
```python
# Test generate() with mocked response
# Test stream() with mocked async iterator
# Test system message extraction
# Test error handling
```

### CREATE worker/tests/test_models_factory.py

- **IMPLEMENT**: Tests for factory function
- **PATTERN**: Standard pytest patterns
- **IMPORTS**: `import pytest; from models.factory import create_model_provider; from models.types import ModelProvider; from models.exceptions import ConfigurationError`
- **GOTCHA**: Mock settings to avoid requiring real API keys
- **VALIDATE**: `cd worker && uv run pytest tests/test_models_factory.py -v`

**Implementation details:**
```python
# Test OpenAI provider creation
# Test Anthropic provider creation
# Test missing API key raises ConfigurationError
# Test default model and config
```

---

## TESTING STRATEGY

### Unit Tests

**Scope**: Test each component in isolation with mocked dependencies

**Requirements**:
- Mock all external SDK calls (AsyncOpenAI, AsyncAnthropic)
- Test both success and error paths
- Verify message format conversions
- Test configuration validation
- Use pytest-asyncio for async tests

**Coverage Target**: 80%+ line coverage

### Integration Tests

**Scope**: Test factory integration with providers

**Requirements**:
- Test factory creates correct provider based on config
- Test provider initialization with settings
- Mock SDK clients but test full provider interface
- Verify error propagation through layers

### Edge Cases

**Critical edge cases to test**:
1. Missing API keys (should raise ConfigurationError)
2. Invalid model names (should raise ProviderError)
3. Empty message lists (should raise InvalidRequestError)
4. Rate limit errors (should raise RateLimitError with retry info)
5. Network errors (should raise ProviderError with context)
6. Streaming interruption (should handle gracefully)
7. System message handling in Anthropic (separate from messages)
8. Token limit exceeded (should raise InvalidRequestError)

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature correctness.

### Level 1: Syntax & Style

```bash
cd worker && uv run ruff check models/ tests/test_models_*.py
```

### Level 2: Type Checking (Optional)

```bash
cd worker && uv run python -m py_compile models/*.py
```

### Level 3: Unit Tests

```bash
cd worker && uv run pytest tests/test_models_base.py -v
cd worker && uv run pytest tests/test_models_openai.py -v
cd worker && uv run pytest tests/test_models_anthropic.py -v
cd worker && uv run pytest tests/test_models_factory.py -v
```

### Level 4: Full Test Suite

```bash
cd worker && uv run pytest tests/ -v --tb=short
```

### Level 5: Import Validation

```bash
cd worker && uv run python -c "from models import create_model_provider, ModelProvider, Message, CompletionResponse; print('✓ All imports successful')"
```

### Level 6: Manual Validation

**Test OpenAI provider** (requires OPENAI_API_KEY in .env):
```python
# worker/manual_test_openai.py
import asyncio
from models import create_model_provider, ModelProvider, Message

async def test():
    provider = create_model_provider(ModelProvider.OPENAI)
    messages = [Message(role="user", content="Say hello")]
    response = await provider.generate(messages)
    print(f"Response: {response.content}")

asyncio.run(test())
```

**Test Anthropic provider** (requires ANTHROPIC_API_KEY in .env):
```python
# worker/manual_test_anthropic.py
import asyncio
from models import create_model_provider, ModelProvider, Message

async def test():
    provider = create_model_provider(ModelProvider.ANTHROPIC)
    messages = [Message(role="user", content="Say hello")]
    response = await provider.generate(messages)
    print(f"Response: {response.content}")

asyncio.run(test())
```

---

## ACCEPTANCE CRITERIA

- [ ] ModelProvider enum supports 'openai' and 'anthropic'
- [ ] Message, ModelConfig, CompletionResponse types are defined with Pydantic
- [ ] Custom exceptions (ModelError, ProviderError, ConfigurationError, etc.) are implemented
- [ ] Abstract ModelProvider base class defines generate() and stream() methods
- [ ] OpenAIProvider implements full interface with AsyncOpenAI client
- [ ] AnthropicProvider implements full interface with AsyncAnthropic client
- [ ] Factory function creates correct provider based on configuration
- [ ] Configuration loads from environment variables (.env file)
- [ ] All validation commands pass with zero errors
- [ ] Unit test coverage ≥80% for models package
- [ ] All tests use mocked SDK clients (no real API calls)
- [ ] Error handling wraps provider errors in custom exceptions
- [ ] Streaming support works for both providers
- [ ] Logging uses structlog for all API calls
- [ ] Package exports clean public API via __init__.py

---

## COMPLETION CHECKLIST

- [ ] All tasks completed in order
- [ ] Each task validation passed immediately
- [ ] All validation commands executed successfully
- [ ] Full test suite passes (unit tests)
- [ ] No linting errors (ruff check passes)
- [ ] Manual testing confirms both providers work (optional, requires API keys)
- [ ] Acceptance criteria all met
- [ ] Code follows project conventions (snake_case, async patterns, structlog)

---

## NOTES

### Design Decisions

**Why Abstract Base Class over Protocol?**
- ABC provides runtime enforcement of interface implementation
- Clearer for inheritance-based design
- Better error messages when methods not implemented

**Why Separate System Messages for Anthropic?**
- Anthropic API requires system parameter separate from messages array
- OpenAI includes system messages in messages array
- Provider implementations handle this difference internally

**Why Factory Pattern?**
- Centralizes provider instantiation logic
- Makes it easy to add new providers
- Simplifies configuration management
- Enables testing with dependency injection

**Why Async-First Design?**
- Orchestrator will be async for non-blocking execution
- Both OpenAI and Anthropic SDKs support async
- Better performance for I/O-bound operations

### Future Enhancements (Out of Scope)

- Retry logic with exponential backoff
- Response caching
- Token counting and cost tracking
- Multi-model routing (try multiple providers)
- Prompt template management
- Function calling / tool use support

### Security Considerations

- API keys loaded from environment variables only
- Never log API keys or full request/response bodies
- Validate all inputs before sending to providers
- Handle rate limits gracefully

### Performance Considerations

- Use async/await for non-blocking I/O
- Stream responses for long completions
- Connection pooling handled by SDK clients
- Consider timeout configuration for production
