# Feature: Model Configuration and Routing

The following plan should be complete, but it's important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils types and models. Import from the right files etc.

## Feature Description

Implement flexible model configuration and intelligent routing that allows:
1. Per-task model selection when creating tasks
2. Default model configuration at the worker level
3. Automatic provider selection based on model name (routing)
4. Model validation and error handling

This enables users to choose different models for different tasks while maintaining sensible defaults, and automatically routes requests to the correct provider (OpenAI or Anthropic) based on the model name.

## User Story

As a **system user**
I want to **specify which AI model to use for each task**
So that **I can optimize for cost, performance, or capabilities based on task requirements**

## Problem Statement

Currently:
- Tasks have a hardcoded default model ("gpt-4-turbo-preview")
- Users cannot specify a model when creating tasks
- No automatic routing between OpenAI and Anthropic based on model name
- Model selection is inflexible and requires code changes

This limits flexibility and makes it difficult to:
- Use different models for different task types
- Take advantage of newer or more cost-effective models
- Switch between providers based on model availability

## Solution Statement

Implement a model configuration and routing system that:
1. **Extends TaskCreate schema** to accept optional model parameter
2. **Creates ModelRouter** to automatically determine provider from model name
3. **Updates factory** to use router for provider selection
4. **Adds validation** for supported models and configurations
5. **Maintains backward compatibility** with existing default behavior

## Feature Metadata

**Feature Type**: Enhancement
**Estimated Complexity**: Medium
**Primary Systems Affected**: backend/schemas, worker/models, worker/config
**Dependencies**: Existing model abstraction layer

---

## CONTEXT REFERENCES

### Relevant Codebase Files IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

- `backend/app/schemas/task.py` (lines 7-13) - Why: TaskCreate schema needs model field
- `backend/app/models/task.py` (lines 17-33) - Why: Task model with existing model field
- `backend/app/routers/tasks.py` (lines 22-28) - Why: Task creation endpoint
- `worker/models/factory.py` (lines 1-32) - Why: Current factory implementation
- `worker/models/types.py` (lines 6-9) - Why: ProviderType enum
- `worker/config.py` (lines 1-17) - Why: Current configuration structure

### New Files to Create

- `worker/models/router.py` - Model routing logic to determine provider from model name
- `worker/models/registry.py` - Model registry with supported models and their providers
- `worker/tests/test_model_router.py` - Tests for routing logic
- `worker/tests/test_model_registry.py` - Tests for model registry

### Relevant Documentation YOU SHOULD READ THESE BEFORE IMPLEMENTING!

- [OpenAI Models](https://platform.openai.com/docs/models)
  - Specific section: Available models list
  - Why: Need to know which models belong to OpenAI
- [Anthropic Models](https://docs.anthropic.com/claude/docs/models-overview)
  - Specific section: Claude model names
  - Why: Need to know which models belong to Anthropic
- [Pydantic Field Validation](https://docs.pydantic.dev/latest/concepts/fields/)
  - Specific section: Optional fields and defaults
  - Why: Adding optional model field to TaskCreate

### Patterns to Follow

**Naming Conventions:**
```python
# Classes: PascalCase
class ModelRouter:
    pass

# Functions: snake_case
def get_provider_for_model(model: str) -> ProviderType:
    pass

# Constants: UPPER_SNAKE_CASE
OPENAI_MODELS = ["gpt-4", "gpt-3.5-turbo"]
```

**Pydantic Schema Pattern:**
```python
# From backend/app/schemas/task.py
class TaskCreate(BaseModel):
    goal: str = Field(..., min_length=1)
    skill: str | None = Field(None, max_length=100)
    # Add: model field with default
```

**Configuration Pattern:**
```python
# From worker/config.py
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")
    default_model: str = "gpt-4"
```

**Factory Pattern:**
```python
# From worker/models/factory.py
def create_model_provider(
    provider: ProviderType | None = None,
    model: str | None = None,
    config: ModelConfig | None = None,
) -> BaseModelProvider:
    # Use router to determine provider if not specified
```

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation

Create model registry and routing infrastructure.

**Tasks:**
- Define model registry with supported models
- Implement model router for provider selection
- Add model validation logic

### Phase 2: Core Implementation

Update schemas, models, and factory to support per-task model selection.

**Tasks:**
- Update TaskCreate schema with optional model field
- Update task creation endpoint to use model parameter
- Integrate router into factory
- Update configuration with model defaults

### Phase 3: Integration

Connect all components and ensure backward compatibility.

**Tasks:**
- Update factory to use router
- Ensure default behavior is maintained
- Add error handling for unsupported models

### Phase 4: Testing & Validation

Comprehensive testing of routing and configuration.

**Tasks:**
- Test model routing for all supported models
- Test per-task model selection via API
- Test default model behavior
- Test error cases (invalid models, missing API keys)

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### CREATE worker/models/registry.py

- **IMPLEMENT**: Model registry with supported models mapped to providers
- **PATTERN**: Simple dictionary-based registry with validation
- **IMPORTS**: `from models.types import ProviderType`
- **GOTCHA**: Keep model names lowercase for case-insensitive matching
- **VALIDATE**: `cd worker && uv run python -c "from models.registry import MODEL_REGISTRY, get_provider_for_model; print(get_provider_for_model('gpt-4'))"`

**Implementation details:**
```python
# Define MODEL_REGISTRY dict mapping model names to ProviderType
# Common OpenAI models: gpt-4, gpt-4-turbo, gpt-3.5-turbo, etc.
# Common Anthropic models: claude-3-opus, claude-3-sonnet, claude-3-haiku, etc.
# Function: get_provider_for_model(model: str) -> ProviderType
# Function: is_model_supported(model: str) -> bool
# Function: get_supported_models() -> list[str]
```

### CREATE worker/models/router.py

- **IMPLEMENT**: Model router to determine provider from model name
- **PATTERN**: Strategy pattern for routing logic
- **IMPORTS**: `from models.registry import get_provider_for_model, is_model_supported; from models.types import ProviderType; from models.exceptions import ConfigurationError`
- **GOTCHA**: Handle model name variations (case, prefixes)
- **VALIDATE**: `cd worker && uv run python -c "from models.router import ModelRouter; router = ModelRouter(); print(router.route('gpt-4'))"`

**Implementation details:**
```python
# ModelRouter class with:
# - route(model: str) -> ProviderType
# - validate_model(model: str) -> None (raises if unsupported)
# - normalize_model_name(model: str) -> str (lowercase, strip)
```

### UPDATE backend/app/schemas/task.py

- **IMPLEMENT**: Add optional model field to TaskCreate
- **PATTERN**: backend/app/schemas/task.py:7-13
- **IMPORTS**: No new imports needed
- **GOTCHA**: Make field optional with default None, backend will use Task model default
- **VALIDATE**: `cd backend && uv run python -c "from app.schemas.task import TaskCreate; t = TaskCreate(conversation_id='00000000-0000-0000-0000-000000000000', project_id='00000000-0000-0000-0000-000000000000', goal='test', model='gpt-4'); print(t.model)"`

**Implementation details:**
```python
# Add to TaskCreate:
# model: str | None = Field(None, max_length=100)
```

### UPDATE worker/models/factory.py

- **IMPLEMENT**: Integrate router to auto-determine provider from model name
- **PATTERN**: worker/models/factory.py:9-31
- **IMPORTS**: `from models.router import ModelRouter`
- **GOTCHA**: Only use router if provider not explicitly specified
- **VALIDATE**: `cd worker && uv run python -c "from models.factory import create_model_provider; print('Factory updated')"`

**Implementation details:**
```python
# Add router = ModelRouter() at module level
# In create_model_provider():
# - If provider is None and model is specified, use router.route(model)
# - Keep existing logic for explicit provider parameter
```

### UPDATE worker/config.py

- **IMPLEMENT**: Add model-related configuration options
- **PATTERN**: worker/config.py:5-16
- **IMPORTS**: No new imports
- **GOTCHA**: Keep backward compatibility with existing default_model
- **VALIDATE**: `cd worker && uv run python -c "from config import settings; print(settings.default_model)"`

**Implementation details:**
```python
# Add optional fields:
# default_openai_model: str = "gpt-4-turbo"
# default_anthropic_model: str = "claude-3-opus-20240229"
# Keep existing default_model for backward compatibility
```

### CREATE worker/tests/test_model_registry.py

- **IMPLEMENT**: Tests for model registry
- **PATTERN**: worker/tests/test_models_base.py
- **IMPORTS**: `import pytest; from models.registry import get_provider_for_model, is_model_supported, MODEL_REGISTRY; from models.types import ProviderType`
- **GOTCHA**: Test case-insensitive matching
- **VALIDATE**: `cd worker && uv run pytest tests/test_model_registry.py -v`

**Implementation details:**
```python
# Test get_provider_for_model with OpenAI models
# Test get_provider_for_model with Anthropic models
# Test is_model_supported for valid/invalid models
# Test case-insensitive model names
# Test unknown model raises error
```

### CREATE worker/tests/test_model_router.py

- **IMPLEMENT**: Tests for model router
- **PATTERN**: worker/tests/test_models_factory.py
- **IMPORTS**: `import pytest; from models.router import ModelRouter; from models.types import ProviderType; from models.exceptions import ConfigurationError`
- **GOTCHA**: Test normalization of model names
- **VALIDATE**: `cd worker && uv run pytest tests/test_model_router.py -v`

**Implementation details:**
```python
# Test route() returns correct provider for OpenAI models
# Test route() returns correct provider for Anthropic models
# Test validate_model() raises for unsupported models
# Test normalize_model_name() handles case and whitespace
```

### UPDATE worker/models/__init__.py

- **IMPLEMENT**: Export router and registry functions
- **PATTERN**: worker/models/__init__.py:1-19
- **IMPORTS**: Add router and registry exports
- **GOTCHA**: Keep existing exports intact
- **VALIDATE**: `cd worker && uv run python -c "from models import ModelRouter, get_provider_for_model; print('Exports updated')"`

**Implementation details:**
```python
# Add to imports:
# from models.router import ModelRouter
# from models.registry import get_provider_for_model, is_model_supported
# Add to __all__
```

---

## TESTING STRATEGY

### Unit Tests

**Scope**: Test each component in isolation

**Requirements**:
- Test model registry with all supported models
- Test router logic for provider determination
- Test factory integration with router
- Test schema validation with model field
- Mock settings to avoid requiring real API keys

**Coverage Target**: 80%+ line coverage

### Integration Tests

**Scope**: Test end-to-end model selection flow

**Requirements**:
- Test task creation with explicit model via API
- Test task creation without model (uses default)
- Test factory creates correct provider based on model
- Test error handling for unsupported models

### Edge Cases

**Critical edge cases to test**:
1. Unknown model name (should raise ConfigurationError)
2. Case variations in model names (GPT-4, gpt-4, Gpt-4)
3. Model name with whitespace
4. Empty model string
5. Model specified but no API key for that provider
6. Backward compatibility (existing code without model parameter)

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature correctness.

### Level 1: Syntax & Style

```bash
cd worker && uv run ruff check models/registry.py models/router.py
cd backend && uv run ruff check app/schemas/task.py
```

### Level 2: Unit Tests

```bash
cd worker && uv run pytest tests/test_model_registry.py -v
cd worker && uv run pytest tests/test_model_router.py -v
cd worker && uv run pytest tests/test_models_factory.py -v
```

### Level 3: Full Test Suite

```bash
cd worker && uv run pytest tests/ -v --tb=short
cd backend && uv run pytest tests/ -v --tb=short
```

### Level 4: Manual Validation

**Test model routing:**
```python
# worker/manual_test_routing.py
from models.router import ModelRouter
from models.registry import get_provider_for_model

router = ModelRouter()
print(f"gpt-4 -> {router.route('gpt-4')}")
print(f"claude-3-opus -> {router.route('claude-3-opus-20240229')}")
```

**Test task creation with model:**
```bash
# Create task with specific model
curl -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "00000000-0000-0000-0000-000000000000",
    "project_id": "00000000-0000-0000-0000-000000000000",
    "goal": "Test task",
    "model": "gpt-4"
  }'
```

---

## ACCEPTANCE CRITERIA

- [ ] ModelRegistry defines all supported OpenAI and Anthropic models
- [ ] ModelRouter correctly routes model names to appropriate providers
- [ ] TaskCreate schema accepts optional model parameter
- [ ] Task creation API accepts and stores model parameter
- [ ] Factory uses router to determine provider when model specified
- [ ] Default model behavior maintained when no model specified
- [ ] All validation commands pass with zero errors
- [ ] Unit test coverage ≥80% for new components
- [ ] Integration tests verify end-to-end model selection
- [ ] Error handling for unsupported models works correctly
- [ ] Case-insensitive model name matching works
- [ ] Backward compatibility maintained (existing code works)

---

## COMPLETION CHECKLIST

- [ ] All tasks completed in order
- [ ] Each task validation passed immediately
- [ ] All validation commands executed successfully
- [ ] Full test suite passes (worker + backend)
- [ ] No linting errors
- [ ] Manual testing confirms model selection works
- [ ] Acceptance criteria all met
- [ ] Code follows project conventions

---

## NOTES

### Design Decisions

**Why Registry Pattern?**
- Centralized model-to-provider mapping
- Easy to add new models
- Simple validation logic
- Clear source of truth

**Why Router Pattern?**
- Separates routing logic from factory
- Testable in isolation
- Extensible for future routing strategies
- Clean separation of concerns

**Why Optional Model Field?**
- Maintains backward compatibility
- Allows gradual adoption
- Sensible defaults for common use cases
- Flexibility for advanced users

### Model Name Conventions

**OpenAI Models:**
- gpt-4, gpt-4-turbo, gpt-4-turbo-preview
- gpt-3.5-turbo, gpt-3.5-turbo-16k
- All lowercase with hyphens

**Anthropic Models:**
- claude-3-opus-20240229
- claude-3-sonnet-20240229
- claude-3-haiku-20240307
- Include date suffix for versioning

### Future Enhancements (Out of Scope)

- Model capability detection (context length, features)
- Cost-based model selection
- Automatic fallback to alternative models
- Model performance tracking
- Dynamic model discovery from provider APIs

### Security Considerations

- Validate model names to prevent injection
- Ensure API keys exist before routing
- Log model selection for audit trails
- Rate limit per model if needed

### Performance Considerations

- Registry lookup is O(1) dictionary access
- Router adds minimal overhead
- No additional API calls for routing
- Cache provider determination if needed
