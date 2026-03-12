# Feature: Skill System

The following plan should be complete, but it's important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils types and models. Import from the right files etc.

## Feature Description

Implement a lightweight skill system that provides task templates with predefined system prompts, tool restrictions, and output formats. Skills configure the agent's behavior for specific task types (research reports, web page generation, file analysis), making it easier for users to get consistent, high-quality results for common workflows.

Skills are NOT complex plugins or extensions - they are simple Python classes that define:
1. A system prompt that guides the agent's behavior
2. A list of allowed tools the agent can use
3. Expected output format
4. Example tasks for documentation

## User Story

As a **Badgers platform user**
I want to **select a skill template when creating tasks**
So that **the agent follows best practices for that task type and produces consistent, structured outputs**

## Problem Statement

Currently, the agent has access to all tools and no specialized guidance for different task types. This leads to:
- Inconsistent output quality across different task types
- Agent may use inappropriate tools for the task
- Users must provide detailed instructions for common workflows
- No standardized output formats (reports, web pages, analysis)

Users need pre-configured templates for common task types that:
- Guide the agent with task-specific system prompts
- Restrict tools to only what's needed for that task type
- Ensure consistent output formats
- Provide better results with less user instruction

## Solution Statement

Implement a skill system with three built-in skill templates:

1. **research_report**: Web research with structured markdown reports
2. **webpage**: HTML/CSS/JS code generation
3. **file_analysis**: Document analysis with insights and summaries

Each skill defines:
- System prompt with role and instructions
- Allowed tools list (subset of available tools)
- Output format specification
- Example tasks for user guidance

The orchestrator loads the skill configuration when creating an agent and applies the system prompt and tool restrictions automatically.

## Feature Metadata

**Feature Type**: New Capability
**Estimated Complexity**: Medium
**Primary Systems Affected**: worker/skills, worker/orchestrator, backend/schemas
**Dependencies**: Existing tool system, agent orchestrator

---

## CONTEXT REFERENCES

### Relevant Codebase Files IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

- `worker/orchestrator/agent.py` (lines 1-101) - Why: Agent initialization and system prompt handling
- `worker/tools/tool_base.py` (lines 1-40) - Why: Tool interface that skills will reference
- `worker/config.py` (lines 1-18) - Why: Configuration pattern for settings
- `backend/app/schemas/task.py` (lines 7-13) - Why: TaskCreate already has skill field
- `backend/app/models/task.py` (lines 17-33) - Why: Task model already stores skill
- `worker/tests/test_agent.py` - Why: Test pattern for agent components

### New Files to Create

- `worker/skills/base.py` - Base Skill class and interface
- `worker/skills/research_report.py` - Research report skill implementation
- `worker/skills/webpage.py` - Web page generation skill implementation
- `worker/skills/file_analysis.py` - File analysis skill implementation
- `worker/skills/registry.py` - Skill registry for lookup by name
- `worker/tests/test_skills.py` - Unit tests for skill system
- `worker/tests/test_skill_registry.py` - Tests for skill registry

### Relevant Documentation YOU SHOULD READ THESE BEFORE IMPLEMENTING!

- [Python ABC Module](https://docs.python.org/3/library/abc.html)
  - Specific section: Abstract Base Classes
  - Why: Creating skill interface
- [Pydantic BaseModel](https://docs.pydantic.dev/latest/concepts/models/)
  - Specific section: Model configuration
  - Why: Skill configuration validation

### Patterns to Follow

**Naming Conventions:**
```python
# Classes: PascalCase
class ResearchReportSkill(Skill):
    pass

# Functions: snake_case
def get_skill_by_name(name: str) -> Skill:
    pass

# Constants: UPPER_SNAKE_CASE
ALLOWED_TOOLS = ["browser.open", "web.fetch"]
```

**Configuration Pattern:**
```python
# From worker/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")
    default_model: str = "gpt-4"
```

**Tool Interface Pattern:**
```python
# From worker/tools/tool_base.py
class Tool(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass
```

**Agent System Prompt Pattern:**
```python
# From worker/orchestrator/agent.py (line 28-34)
async def run(self, goal: str, system_prompt: str | None = None) -> str:
    if system_prompt:
        self.messages.append(Message(role="system", content=system_prompt))
    self.messages.append(Message(role="user", content=goal))
```

**Testing Pattern:**
```python
# From worker/tests/test_agent.py
import pytest
from unittest.mock import Mock, AsyncMock

@pytest.mark.asyncio
async def test_function():
    # Arrange
    # Act
    # Assert
```

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation

Create base skill interface and registry infrastructure.

**Tasks:**
- Define abstract Skill base class
- Create skill registry for name-based lookup
- Define skill configuration structure

### Phase 2: Core Implementation

Implement the three skill templates.

**Tasks:**
- Implement ResearchReportSkill
- Implement WebPageSkill
- Implement FileAnalysisSkill
- Register all skills in registry

### Phase 3: Integration

Connect skills to agent orchestrator.

**Tasks:**
- Update agent initialization to accept skill parameter
- Load skill configuration and apply system prompt
- Filter tools based on skill's allowed_tools list
- Update worker entry point to use skills

### Phase 4: Testing & Validation

Comprehensive testing of skill system.

**Tasks:**
- Unit tests for each skill
- Test skill registry lookup
- Test agent integration with skills
- Validate tool filtering works correctly

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### CREATE worker/skills/base.py

- **IMPLEMENT**: Abstract base class for skill templates
- **PATTERN**: Python ABC from worker/tools/tool_base.py:15-40
- **IMPORTS**: `from abc import ABC, abstractmethod; from typing import List`
- **GOTCHA**: Use @property for read-only attributes
- **VALIDATE**: `cd worker && uv run python -c "from skills.base import Skill; print('Skill base imported')"`

**Implementation details:**
```python
# Abstract Skill class with:
# - name: str (property)
# - description: str (property)
# - system_prompt: str (property)
# - allowed_tools: List[str] (property) - tool names like "browser.open"
# - output_format: str (property)
# - example_tasks: List[str] (property)
```

### CREATE worker/skills/research_report.py

- **IMPLEMENT**: Research report skill implementation
- **PATTERN**: skills/base.py Skill interface
- **IMPORTS**: `from skills.base import Skill; from typing import List`
- **GOTCHA**: System prompt should be specific and actionable
- **VALIDATE**: `cd worker && uv run python -c "from skills.research_report import ResearchReportSkill; s = ResearchReportSkill(); print(s.name)"`

**Implementation details:**
```python
# ResearchReportSkill class:
# - name = "research_report"
# - description = "Generate structured research reports with web search and citations"
# - system_prompt = "You are a research assistant. Search for information using browser and web tools, extract key facts, and generate a structured markdown report with citations. Include: Executive Summary, Key Findings (with sources), and Conclusion. Use proper markdown formatting with headers, lists, and links."
# - allowed_tools = ["browser.open", "browser.extract", "browser.screenshot", "web.fetch", "file.write", "final.answer"]
# - output_format = "Markdown report with sections: Executive Summary, Findings, Sources"
# - example_tasks = ["Research Tesla Q4 2025 earnings", "Analyze recent AI developments", "Compare cloud provider pricing"]
```

### CREATE worker/skills/webpage.py

- **IMPLEMENT**: Web page generation skill implementation
- **PATTERN**: skills/base.py Skill interface
- **IMPORTS**: `from skills.base import Skill; from typing import List`
- **GOTCHA**: Focus on clean, modern HTML/CSS/JS
- **VALIDATE**: `cd worker && uv run python -c "from skills.webpage import WebPageSkill; s = WebPageSkill(); print(s.name)"`

**Implementation details:**
```python
# WebPageSkill class:
# - name = "webpage"
# - description = "Generate clean, responsive HTML/CSS/JS web pages"
# - system_prompt = "You are a web developer. Generate clean, responsive HTML/CSS/JS code following modern best practices. Use semantic HTML5, mobile-first CSS, and vanilla JavaScript. Include inline styles and scripts unless the page is complex. Ensure accessibility (ARIA labels, alt text). Write the complete HTML file using file.write tool."
# - allowed_tools = ["file.write", "python.run", "final.answer"]
# - output_format = "HTML file with embedded CSS/JS or separate files"
# - example_tasks = ["Create a pricing page with three tiers", "Build a landing page for a SaaS product", "Generate a portfolio page"]
```

### CREATE worker/skills/file_analysis.py

- **IMPLEMENT**: File analysis skill implementation
- **PATTERN**: skills/base.py Skill interface
- **IMPORTS**: `from skills.base import Skill; from typing import List`
- **GOTCHA**: Emphasize data extraction and insights
- **VALIDATE**: `cd worker && uv run python -c "from skills.file_analysis import FileAnalysisSkill; s = FileAnalysisSkill(); print(s.name)"`

**Implementation details:**
```python
# FileAnalysisSkill class:
# - name = "file_analysis"
# - description = "Analyze documents and extract insights with summaries"
# - system_prompt = "You are a data analyst. Read files using file.read, analyze their content, extract key insights, and generate summary reports. Use python.run for data processing if needed. Present findings in a clear, structured format with key metrics, trends, and actionable insights."
# - allowed_tools = ["file.read", "file.list", "python.run", "file.write", "final.answer"]
# - output_format = "Analysis report with key findings, metrics, and visualizations"
# - example_tasks = ["Analyze this CSV and find trends", "Extract key terms from PDF", "Summarize contract terms"]
```

### CREATE worker/skills/registry.py

- **IMPLEMENT**: Skill registry for name-based lookup
- **PATTERN**: worker/models/registry.py:1-50 (model registry pattern)
- **IMPORTS**: `from skills.base import Skill; from skills.research_report import ResearchReportSkill; from skills.webpage import WebPageSkill; from skills.file_analysis import FileAnalysisSkill`
- **GOTCHA**: Use dictionary for O(1) lookup, validate skill names
- **VALIDATE**: `cd worker && uv run python -c "from skills.registry import get_skill, list_skills; print(list_skills())"`

**Implementation details:**
```python
# SKILL_REGISTRY: dict[str, Skill] mapping skill names to instances
# - "research_report": ResearchReportSkill()
# - "webpage": WebPageSkill()
# - "file_analysis": FileAnalysisSkill()
#
# Functions:
# - get_skill(name: str) -> Skill | None
# - list_skills() -> List[str]
# - is_valid_skill(name: str) -> bool
```

### UPDATE worker/skills/__init__.py

- **IMPLEMENT**: Export public API from skills package
- **PATTERN**: worker/models/__init__.py:1-19
- **IMPORTS**: All skill classes and registry functions
- **GOTCHA**: Only export what orchestrator needs
- **VALIDATE**: `cd worker && uv run python -c "from skills import get_skill, list_skills; print('Skills package imported')"`

**Implementation details:**
```python
# Export:
# - Skill (base class)
# - ResearchReportSkill, WebPageSkill, FileAnalysisSkill
# - get_skill, list_skills, is_valid_skill
```

### UPDATE worker/orchestrator/agent.py

- **IMPLEMENT**: Add skill parameter and tool filtering
- **PATTERN**: Existing agent.py:14-26 __init__ method
- **IMPORTS**: `from skills.base import Skill`
- **GOTCHA**: Filter tools before passing to agent, apply system prompt from skill
- **VALIDATE**: `cd worker && uv run python -c "from orchestrator.agent import Agent; print('Agent updated')"`

**Implementation details:**
```python
# Update Agent.__init__ to accept optional skill: Skill | None parameter
# If skill provided:
#   - Filter tools list to only include tools in skill.allowed_tools
#   - Store skill for later use
# Update Agent.run to use skill.system_prompt if skill is provided
```

### CREATE worker/tests/test_skills.py

- **IMPLEMENT**: Unit tests for skill implementations
- **PATTERN**: worker/tests/test_agent.py
- **IMPORTS**: `import pytest; from skills.research_report import ResearchReportSkill; from skills.webpage import WebPageSkill; from skills.file_analysis import FileAnalysisSkill`
- **GOTCHA**: Test all properties return expected values
- **VALIDATE**: `cd worker && uv run pytest tests/test_skills.py -v`

**Implementation details:**
```python
# Test each skill:
# - test_research_report_skill_properties()
# - test_webpage_skill_properties()
# - test_file_analysis_skill_properties()
# - test_skill_allowed_tools_list()
# - test_skill_system_prompt_not_empty()
```

### CREATE worker/tests/test_skill_registry.py

- **IMPLEMENT**: Tests for skill registry
- **PATTERN**: worker/tests/test_model_registry.py
- **IMPORTS**: `import pytest; from skills.registry import get_skill, list_skills, is_valid_skill, SKILL_REGISTRY`
- **GOTCHA**: Test both valid and invalid skill names
- **VALIDATE**: `cd worker && uv run pytest tests/test_skill_registry.py -v`

**Implementation details:**
```python
# - test_get_skill_valid_name()
# - test_get_skill_invalid_name()
# - test_list_skills_returns_all()
# - test_is_valid_skill()
# - test_registry_has_three_skills()
```

---

## TESTING STRATEGY

### Unit Tests

**Framework**: pytest with pytest-asyncio

**Coverage Requirements**: 80%+ for skills module

**Test Structure**:
- Test each skill's properties independently
- Test registry lookup with valid/invalid names
- Test agent integration with skill filtering
- Mock tool execution, focus on configuration

### Integration Tests

**Scope**: Agent with skill configuration end-to-end

**Test Scenarios**:
1. Create agent with research_report skill, verify only allowed tools available
2. Create agent with webpage skill, verify system prompt applied
3. Create agent without skill, verify all tools available
4. Test invalid skill name handling

### Edge Cases

1. **Invalid Skill Name**: get_skill returns None for unknown skill
2. **Empty Allowed Tools**: Skill with no tools should still work
3. **Tool Name Mismatch**: Tool not in allowed_tools should be filtered out
4. **None Skill**: Agent works normally without skill (backward compatibility)

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature correctness.

### Level 1: Syntax & Style

```bash
cd worker && uv run ruff check skills/ tests/test_skills.py tests/test_skill_registry.py
```

### Level 2: Unit Tests

```bash
cd worker && uv run pytest tests/test_skills.py -v
cd worker && uv run pytest tests/test_skill_registry.py -v
```

### Level 3: Full Test Suite

```bash
cd worker && uv run pytest tests/ -v --tb=short
```

### Level 4: Import Validation

```bash
cd worker && uv run python -c "from skills import get_skill, list_skills; print('Available skills:', list_skills())"
cd worker && uv run python -c "from skills import get_skill; skill = get_skill('research_report'); print(f'Skill: {skill.name}, Tools: {len(skill.allowed_tools)}')"
```

### Level 5: Manual Validation

**Test skill loading:**
```python
# worker/manual_test_skills.py
from skills import get_skill, list_skills

print("Available skills:", list_skills())

for skill_name in list_skills():
    skill = get_skill(skill_name)
    print(f"\n{skill.name}:")
    print(f"  Description: {skill.description}")
    print(f"  Allowed tools: {skill.allowed_tools}")
    print(f"  System prompt length: {len(skill.system_prompt)} chars")
```

---

## ACCEPTANCE CRITERIA

- [ ] Skill base class defines interface with all required properties
- [ ] ResearchReportSkill implemented with appropriate tools and prompt
- [ ] WebPageSkill implemented with appropriate tools and prompt
- [ ] FileAnalysisSkill implemented with appropriate tools and prompt
- [ ] Skill registry provides get_skill() and list_skills() functions
- [ ] Registry contains all three skills
- [ ] Agent accepts optional skill parameter
- [ ] Agent filters tools based on skill.allowed_tools when skill provided
- [ ] Agent uses skill.system_prompt when skill provided
- [ ] All validation commands pass with zero errors
- [ ] Unit test coverage ≥80% for skills module
- [ ] Backward compatibility maintained (agent works without skill)
- [ ] Task schema already supports skill field (no changes needed)

---

## COMPLETION CHECKLIST

- [ ] All tasks completed in order
- [ ] Each task validation passed immediately
- [ ] All validation commands executed successfully
- [ ] Full test suite passes (unit tests)
- [ ] No linting errors (ruff check passes)
- [ ] Manual testing confirms skills load correctly
- [ ] Acceptance criteria all met
- [ ] Code follows project conventions (snake_case, type hints)

---

## NOTES

### Design Decisions

**Why Simple Classes Instead of Complex Plugin System?**
- MVP needs lightweight templates, not extensibility
- Simple Python classes are easy to understand and maintain
- No need for dynamic loading or user-defined skills yet
- Can evolve to plugin system in future if needed

**Why Property-Based Interface?**
- Skills are read-only configuration
- Properties enforce immutability
- Clear interface for orchestrator to consume
- Follows Python conventions for configuration objects

**Why Tool Name Strings Instead of Tool Objects?**
- Skills define allowed tool names as strings (e.g., "browser.open")
- Orchestrator filters actual Tool instances by name
- Decouples skill definition from tool implementation
- Easier to define and test

**Why Three Specific Skills?**
- Cover most common use cases from PRD user stories
- Research: information gathering and reporting
- Webpage: code generation and prototyping
- File Analysis: document processing and insights
- Can add more skills incrementally

### Skill System Prompt Guidelines

Good system prompts should:
- Define the agent's role clearly
- Specify expected output format
- Mention which tools to use
- Include quality guidelines (citations, formatting, etc.)
- Be concise but comprehensive (2-4 sentences)

### Tool Filtering Logic

```python
# Pseudocode for tool filtering
if skill:
    filtered_tools = [t for t in all_tools if t.name in skill.allowed_tools]
else:
    filtered_tools = all_tools
```

### Future Enhancements (Out of Scope)

- User-defined custom skills
- Skill composition (combining multiple skills)
- Dynamic skill loading from files
- Skill marketplace or sharing
- Per-skill configuration (temperature, max_tokens)
- Skill versioning

### Integration with Existing System

**Task Creation Flow:**
1. User creates task with optional skill parameter
2. Backend stores skill name in Task model (already supported)
3. Worker loads task and looks up skill from registry
4. Worker creates agent with skill configuration
5. Agent applies system prompt and tool filtering
6. Task executes with skill-specific behavior

**No Breaking Changes:**
- Task schema already has skill field (optional)
- Agent already accepts system_prompt parameter
- Tool filtering is additive (doesn't break existing code)
- Skills are optional (backward compatible)

---

## CONFIDENCE SCORE

**8/10** - High confidence for one-pass implementation success

**Reasoning:**
- Clear requirements from PRD with specific skill definitions
- Simple implementation (Python classes with properties)
- No external dependencies or complex integrations
- Existing patterns to follow (tool interface, registry pattern)
- Comprehensive task breakdown with validation
- Agent already supports system prompts

**Risk Factors:**
- Tool filtering logic needs careful implementation
- Need to ensure tool names match exactly
- Agent integration requires understanding existing code flow
- Testing tool filtering may require mocking

**Mitigation:**
- Each task has immediate validation command
- Test-driven approach catches issues early
- Tool name matching is straightforward string comparison
- Can reference existing tool implementations for names

