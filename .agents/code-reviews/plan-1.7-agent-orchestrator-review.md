# Code Review: Basic Agent Orchestrator (Plan 1.7)

**Review Date**: 2026-03-12
**Reviewer**: Claude (Automated Code Review)
**Scope**: Agent orchestrator with tool calling support

## Stats

- Files Modified: 0
- Files Added: 11
- Files Deleted: 0
- New lines: 606
- Deleted lines: 0

## Summary

The agent orchestrator implementation is well-structured with clean separation of concerns. However, there are several security vulnerabilities (path traversal), error handling issues, and a critical bug with tool format selection that need to be addressed before production use.

## Issues Found

### Issue 1: Path Traversal Vulnerability in File Tools

**severity**: critical
**file**: worker/tools/file.py
**line**: 33, 72, 111
**issue**: Path traversal vulnerability allows access outside workspace
**detail**: The code uses `Path(self.workspace_dir) / path` without validating that the resulting path stays within workspace_dir. An attacker could use paths like `../../etc/passwd` to access files outside the sandbox.
**suggestion**: Add path validation to ensure resolved path is within workspace:

```python
full_path = (Path(self.workspace_dir) / path).resolve()
workspace = Path(self.workspace_dir).resolve()
if not full_path.is_relative_to(workspace):
    return ToolResult(success=False, output="", error="Path outside workspace not allowed")
```

---

### Issue 2: Tool Format Mismatch

**severity**: high
**file**: worker/orchestrator/agent.py
**line**: 36
**issue**: Always uses OpenAI tool format regardless of model provider
**detail**: Line 36 calls `to_openai_tool()` for all tools, but Anthropic provider expects different format. This will cause tool calling to fail with Anthropic models.
**suggestion**: Detect provider type and use appropriate format:

```python
# Check if model is Anthropic provider
if hasattr(self.model, '__class__') and 'Anthropic' in self.model.__class__.__name__:
    tool_schemas = [tool.to_anthropic_tool() for tool in self.tools.values()]
else:
    tool_schemas = [tool.to_openai_tool() for tool in self.tools.values()]
```

---


### Issue 3: JSON Parsing Error Not Handled

**severity**: high
**file**: worker/models/openai_compat.py
**line**: 35
**issue**: json.loads() can raise JSONDecodeError without handling
**detail**: If OpenAI returns malformed JSON in tool arguments, json.loads() will raise JSONDecodeError and crash the agent. This should be caught and converted to ModelError.
**suggestion**: Add try-except around JSON parsing:

```python
try:
    arguments=json.loads(tc.function.arguments)
except json.JSONDecodeError as e:
    raise ModelError(f"Invalid JSON in tool arguments: {e}")
```

---

### Issue 4: No File Size Limit in FileReadTool

**severity**: medium
**file**: worker/tools/file.py
**line**: 78
**issue**: Reading files without size limit can cause memory exhaustion
**detail**: The code reads entire file into memory with read_text(). A malicious or accidental large file (e.g., 10GB log file) will exhaust memory and crash the worker.
**suggestion**: Add file size check before reading:

```python
file_size = full_path.stat().st_size
if file_size > 10 * 1024 * 1024:  # 10MB limit
    return ToolResult(success=False, output="", error=f"File too large: {file_size} bytes")
content = full_path.read_text(encoding="utf-8")
```

---

### Issue 5: Overly Broad Exception Handling

**severity**: medium
**file**: worker/orchestrator/agent.py
**line**: 74-76
**issue**: Catching all exceptions loses original error context
**detail**: The broad `except Exception` catches all errors including KeyboardInterrupt, SystemExit, etc., and wraps them in AgentExecutionError. This makes debugging difficult and can mask critical errors.
**suggestion**: Catch specific exceptions or re-raise system exceptions:

```python
except (ModelError, ToolExecutionError) as e:
    logger.error("agent_error", task_run_id=str(self.task_run_id), error=str(e))
    raise AgentExecutionError(f"Agent execution failed: {e}") from e
except Exception as e:
    logger.error("unexpected_error", task_run_id=str(self.task_run_id), error=str(e))
    raise
```

---
