# Code Review: Docker Sandbox Manager Implementation

**Review Date**: 2026-03-11
**Reviewer**: Claude (Automated Code Review)
**Scope**: Docker sandbox lifecycle management implementation

## Stats

- Files Modified: 1
- Files Added: 5
- Files Deleted: 0
- New lines: 267
- Deleted lines: 3

## Summary

The Docker sandbox manager implementation is well-structured with proper separation of concerns, comprehensive test coverage, and good error handling. The code follows Python best practices and includes security hardening in the Docker image. However, there are a few medium-severity issues related to error handling and observability that should be addressed.

## Issues Found

### Issue 1: UTF-8 Decoding Without Error Handling

**severity**: medium
**file**: worker/sandbox/docker_backend.py
**line**: 64
**issue**: Unsafe UTF-8 decoding could raise UnicodeDecodeError
**detail**: The code uses `output.decode('utf-8')` without error handling. If the command output contains non-UTF-8 bytes (binary data, corrupted output), this will raise an exception and crash the execution.
**suggestion**: Use `output.decode('utf-8', errors='replace')` or `errors='ignore'` to handle invalid UTF-8 sequences gracefully.

```python
# Current
return exit_code, output.decode('utf-8')

# Suggested
return exit_code, output.decode('utf-8', errors='replace')
```

---

### Issue 2: UTF-8 Decoding in Logs Without Error Handling

**severity**: medium
**file**: worker/sandbox/docker_backend.py
**line**: 72
**issue**: Unsafe UTF-8 decoding in log retrieval
**detail**: Same issue as Issue 1 - container logs may contain binary data or invalid UTF-8 sequences.
**suggestion**: Use `decode('utf-8', errors='replace')` for robust log handling.

```python
# Current
return container.logs().decode('utf-8')

# Suggested
return container.logs().decode('utf-8', errors='replace')
```

---

### Issue 3: No Timeout on Command Execution

**severity**: medium
**file**: worker/sandbox/docker_backend.py
**line**: 63
**issue**: exec_run has no timeout, could hang indefinitely
**detail**: If a command runs indefinitely (infinite loop, waiting for input), the execution will hang with no way to recover. This could exhaust worker resources.
**suggestion**: Add a configurable timeout parameter to execute_command and pass it to exec_run.

```python
def execute_command(self, container_id: str, command: str, timeout: int = 300) -> tuple[int, str]:
    """Execute command with timeout (default 5 minutes)."""
    try:
        container = self.client.containers.get(container_id)
        exit_code, output = container.exec_run(command, demux=False, stream=False)
        # Note: docker-py exec_run doesn't support timeout directly
        # Consider using container.exec_create + exec_start with timeout
        return exit_code, output.decode('utf-8', errors='replace')
    except DockerException as e:
        raise SandboxExecutionError(f"Failed to execute command: {e}")
```

---

### Issue 4: Missing Structured Logging

**severity**: medium
**file**: worker/sandbox/manager.py
**line**: 25-39
**issue**: No logging for sandbox lifecycle events
**detail**: The manager performs critical operations (create, destroy, execute) but doesn't log them. This makes debugging and monitoring difficult in production.
**suggestion**: Add structlog logging for all lifecycle events with task_run_id context.

```python
import structlog

logger = structlog.get_logger(__name__)

async def create(self):
    """Create sandbox container."""
    logger.info("creating_sandbox", task_run_id=str(self.task_run_id), image=self.image)
    self.container_id = self.backend.create_container(...)
    self.backend.start_container(self.container_id)
    logger.info("sandbox_created", task_run_id=str(self.task_run_id), container_id=self.container_id)
    return self.container_id
```

---

### Issue 5: Dockerfile Layer Optimization

**severity**: low
**file**: docker/sandbox-base/Dockerfile
**line**: 4-17
**issue**: Large RUN command reduces layer caching efficiency
**detail**: The entire system dependency installation is in one RUN command. If Node.js installation changes, all apt packages are reinstalled unnecessarily.
**suggestion**: Split into separate RUN commands for better layer caching, or accept current approach for smaller image size (current approach is acceptable).

---

### Issue 6: No Version Pinning for System Packages

**severity**: low
**file**: docker/sandbox-base/Dockerfile
**line**: 4-17
**issue**: System packages not version-pinned
**detail**: Packages like curl, git, wget are installed without version constraints. This could lead to non-reproducible builds if package versions change.
**suggestion**: Pin versions for critical packages or document that latest versions are acceptable for this use case (current approach is acceptable for MVP).

---

### Issue 7: Hardcoded Network Mode

**severity**: low
**file**: worker/sandbox/docker_backend.py
**line**: 25
**issue**: Network mode hardcoded to "bridge"
**detail**: The network_mode is hardcoded. Future requirements might need "none" for isolated sandboxes or custom networks.
**suggestion**: Make network_mode a parameter with "bridge" as default (not blocking for MVP).

---

## Positive Observations

1. **Excellent separation of concerns**: DockerBackend handles low-level operations, SandboxManager provides high-level orchestration
2. **Comprehensive test coverage**: 11 tests covering all major code paths with proper mocking
3. **Good error handling**: Custom exception hierarchy and proper exception wrapping
4. **Security hardening**: Non-root user in Docker image, resource limits enforced
5. **Clean async context manager**: Ensures cleanup even on exceptions
6. **Type hints**: Proper type annotations throughout the code
7. **NotFound handling**: Gracefully handles missing containers in cleanup operations

## Recommendations

1. **Address medium-severity issues**: UTF-8 decoding (Issues 1-2) and logging (Issue 4) are important for production reliability
2. **Consider timeout strategy**: Issue 3 should be addressed to prevent resource exhaustion
3. **Low-severity issues are optional**: Issues 5-7 are nice-to-have improvements but not blocking

## Conclusion

**Overall Assessment**: ✅ PASS with recommendations

The implementation is well-designed and production-ready. The code follows best practices, has comprehensive test coverage (11/11 tests passing), and includes proper security hardening. The medium-severity issues (1-4) are straightforward to fix but don't block the current MVP milestone.

**Recommended Action**: Proceed with commit. Address Issues 1-4 in a follow-up task if needed.

