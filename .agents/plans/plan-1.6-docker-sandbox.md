# Feature: Docker Sandbox Manager Foundation

## Feature Description

Implement sandbox lifecycle management for isolated task execution environments. The sandbox manager creates, manages, and destroys Docker containers that provide secure, isolated environments for agent tool execution. Each TaskRun gets its own dedicated sandbox with resource limits and proper cleanup.

This establishes the foundation for the agent execution workflow: when a task run starts, create a sandbox; execute tools within it; capture outputs; destroy sandbox when complete.

## User Story

As a backend developer
I want to manage Docker sandbox lifecycles programmatically
So that each task execution runs in an isolated, secure environment with proper resource limits and cleanup

## Problem Statement

The worker currently has no sandbox management implementation. To enable task execution, we need:
- Docker container lifecycle management (create, start, stop, remove)
- Resource limit enforcement (CPU, memory)
- Sandbox session tracking in database
- Proper cleanup on success and failure
- Base Docker image with necessary tools

## Solution Statement

Implement a sandbox management system with two main components:
1. **SandboxManager** - High-level lifecycle orchestration and database integration
2. **DockerBackend** - Low-level Docker SDK operations

Key architectural decisions:
- One container per TaskRun (1:1 mapping)
- Containers are ephemeral (destroyed after use)
- Resource limits enforced at container creation
- Base image includes Python, Node.js, and common tools

## Feature Metadata

**Feature Type**: New Capability
**Estimated Complexity**: High
**Primary Systems Affected**: Worker (sandbox management), Backend (SandboxSession tracking)
**Dependencies**: Docker SDK (docker-py), Docker daemon, Base Docker image

---

## CONTEXT REFERENCES

### Relevant Codebase Files

**IMPORTANT: READ THESE BEFORE IMPLEMENTING!**

- `backend/app/models/sandbox.py` - SandboxSession model with container_id, image, resource limits
- `backend/app/models/task.py` - TaskRun model with sandbox_session relationship
- `worker/pyproject.toml` - Dependencies (docker>=7.0.0 already included)
- `docker/sandbox-base/Dockerfile` - Existing base image to enhance

### New Files to Create

- `worker/sandbox/manager.py` - High-level sandbox lifecycle manager
- `worker/sandbox/docker_backend.py` - Docker SDK wrapper
- `worker/sandbox/exceptions.py` - Custom exceptions for sandbox operations
- `worker/tests/test_sandbox_manager.py` - Unit tests for manager
- `worker/tests/test_docker_backend.py` - Unit tests for Docker backend

### Relevant Documentation

**YOU SHOULD READ THESE BEFORE IMPLEMENTING!**

- [Docker SDK for Python](https://docker-py.readthedocs.io/en/stable/)
  - Container management API
  - Why: Core library for Docker operations
- [Docker SDK Containers](https://docker-py.readthedocs.io/en/stable/containers.html)
  - create(), start(), stop(), remove() methods
  - Why: Container lifecycle operations
- [Docker Resource Constraints](https://docs.docker.com/config/containers/resource_constraints/)
  - CPU and memory limits
  - Why: Enforce resource limits for security


### Patterns to Follow

**Async Context Manager Pattern** (for resource cleanup):
```python
class SandboxManager:
    async def __aenter__(self):
        # Create sandbox
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Cleanup sandbox
        await self.destroy()
```

**Exception Handling Pattern**:
```python
class SandboxError(Exception):
    """Base exception for sandbox operations"""
    pass

class SandboxCreationError(SandboxError):
    """Failed to create sandbox"""
    pass

class SandboxExecutionError(SandboxError):
    """Failed to execute command in sandbox"""
    pass
```

**Docker SDK Pattern**:
```python
import docker

client = docker.from_env()
container = client.containers.create(
    image="badgers-sandbox:latest",
    detach=True,
    mem_limit="512m",
    cpu_quota=50000,
    network_mode="bridge"
)
container.start()
```

**Database Integration Pattern** (from existing models):
```python
from backend.app.models.sandbox import SandboxSession
from backend.app.database import get_db

async with get_db() as db:
    session = SandboxSession(
        task_run_id=run_id,
        container_id=container.id,
        image="badgers-sandbox:latest"
    )
    db.add(session)
    await db.commit()
```

---

## IMPLEMENTATION PLAN

### Phase 1: Docker Backend

Implement low-level Docker SDK wrapper for container operations.

**Tasks:**
- Create docker_backend.py with DockerBackend class
- Implement create_container, start_container, stop_container, remove_container
- Implement execute_command for running commands in container
- Add resource limit enforcement
- Create custom exceptions

### Phase 2: Sandbox Manager

Implement high-level sandbox lifecycle orchestration.

**Tasks:**
- Create manager.py with SandboxManager class
- Implement create() method with database integration
- Implement destroy() method with cleanup
- Implement execute() method for command execution
- Add async context manager support

### Phase 3: Base Docker Image

Enhance the base Docker image with necessary tools.

**Tasks:**
- Update Dockerfile with Node.js, additional tools
- Add security hardening
- Build and tag image
- Test image locally

### Phase 4: Testing

Create comprehensive test coverage.

**Tasks:**
- Unit tests for DockerBackend
- Unit tests for SandboxManager
- Integration tests with real Docker daemon
- Mock tests for CI/CD environments

---

## STEP-BY-STEP TASKS

### CREATE worker/sandbox/exceptions.py

- **IMPLEMENT**: Custom exception classes for sandbox operations
- **IMPORTS**: None (base Python exceptions)
- **CLASSES**:
  - `SandboxError` - Base exception
  - `SandboxCreationError` - Container creation failures
  - `SandboxExecutionError` - Command execution failures
  - `SandboxCleanupError` - Cleanup failures
- **VALIDATE**: `cd worker && python -c "from sandbox.exceptions import SandboxError; print('OK')"`

### CREATE worker/sandbox/docker_backend.py

- **IMPLEMENT**: DockerBackend class with container lifecycle methods
- **IMPORTS**: `import docker`, `from docker.errors import DockerException`
- **IMPORTS**: `from .exceptions import SandboxCreationError, SandboxExecutionError`
- **METHODS**:
  - `__init__(self)` - Initialize Docker client
  - `create_container(image, mem_limit, cpu_quota)` - Create container with limits
  - `start_container(container_id)` - Start container
  - `stop_container(container_id, timeout=10)` - Stop container gracefully
  - `remove_container(container_id, force=False)` - Remove container
  - `execute_command(container_id, command)` - Execute command in container
  - `get_container_logs(container_id)` - Get container logs
- **PATTERN**: Use docker.from_env() for client initialization
- **GOTCHA**: Handle DockerException and convert to custom exceptions
- **VALIDATE**: `cd worker && python -c "from sandbox.docker_backend import DockerBackend; print('OK')"`

### CREATE worker/sandbox/manager.py

- **IMPLEMENT**: SandboxManager class with high-level lifecycle management
- **IMPORTS**: `import uuid`, `from datetime import datetime`
- **IMPORTS**: `from .docker_backend import DockerBackend`
- **IMPORTS**: `from .exceptions import SandboxError`
- **METHODS**:
  - `__init__(self, task_run_id, image, mem_limit, cpu_quota)` - Initialize manager
  - `async def create(self)` - Create sandbox and save to database
  - `async def destroy(self)` - Stop and remove container, update database
  - `async def execute(self, command)` - Execute command in sandbox
  - `async def __aenter__(self)` - Context manager entry
  - `async def __aexit__(self, exc_type, exc_val, exc_tb)` - Context manager exit with cleanup
- **PATTERN**: Async context manager for automatic cleanup
- **GOTCHA**: Ensure cleanup happens even on exceptions
- **VALIDATE**: `cd worker && python -c "from sandbox.manager import SandboxManager; print('OK')"`

### UPDATE docker/sandbox-base/Dockerfile

- **IMPLEMENT**: Enhanced base image with Node.js and additional tools
- **ADD**: Node.js 20.x installation
- **ADD**: Additional system packages (jq, vim, wget)
- **ADD**: Security hardening (non-root user)
- **PATTERN**:
```dockerfile
FROM python:3.11-slim

# Install Node.js
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs

# Create non-root user
RUN useradd -m -u 1000 sandbox
USER sandbox
```
- **VALIDATE**: `cd docker/sandbox-base && docker build -t badgers-sandbox:latest .`


### CREATE worker/tests/test_docker_backend.py

- **IMPLEMENT**: Unit tests for DockerBackend class
- **IMPORTS**: `import pytest`, `from unittest.mock import Mock, patch`
- **IMPORTS**: `from sandbox.docker_backend import DockerBackend`
- **IMPORTS**: `from sandbox.exceptions import SandboxCreationError`
- **TEST CASES**:
  - `test_create_container_success` - Verify container creation with limits
  - `test_create_container_failure` - Handle Docker errors
  - `test_start_container` - Verify container start
  - `test_stop_container` - Verify graceful stop
  - `test_remove_container` - Verify container removal
  - `test_execute_command` - Verify command execution
- **PATTERN**: Use mocks for Docker client to avoid requiring Docker daemon
- **VALIDATE**: `cd worker && pytest tests/test_docker_backend.py -v`

### CREATE worker/tests/test_sandbox_manager.py

- **IMPLEMENT**: Unit tests for SandboxManager class
- **IMPORTS**: `import pytest`, `from unittest.mock import AsyncMock, patch`
- **IMPORTS**: `from sandbox.manager import SandboxManager`
- **TEST CASES**:
  - `test_create_sandbox` - Verify sandbox creation and database save
  - `test_destroy_sandbox` - Verify cleanup and database update
  - `test_execute_command` - Verify command execution
  - `test_context_manager` - Verify automatic cleanup
  - `test_cleanup_on_exception` - Verify cleanup happens on errors
- **PATTERN**: Mock DockerBackend and database operations
- **VALIDATE**: `cd worker && pytest tests/test_sandbox_manager.py -v`

---

## TESTING STRATEGY

### Unit Tests

Mock Docker SDK and database operations to test logic without requiring Docker daemon.

**DockerBackend Tests:**
- Container lifecycle operations (create, start, stop, remove)
- Command execution
- Error handling and exception conversion
- Resource limit enforcement

**SandboxManager Tests:**
- High-level lifecycle orchestration
- Database integration (create SandboxSession, update terminated_at)
- Context manager behavior
- Cleanup on success and failure

### Integration Tests

Test with real Docker daemon (optional, for local development).

**Prerequisites:**
- Docker daemon running
- Base image built (`badgers-sandbox:latest`)

**Test Cases:**
- Create real container and verify it exists
- Execute command and verify output
- Stop and remove container
- Verify resource limits are enforced

### Edge Cases

- Docker daemon not available (graceful error)
- Container creation fails (out of resources)
- Container stops unexpectedly during execution
- Cleanup fails (container already removed)
- Database connection fails during create/destroy

---

## VALIDATION COMMANDS

### Level 1: Syntax & Style

```bash
cd worker && uv run ruff check sandbox/
```

**Expected**: All checks passed

### Level 2: Import Validation

```bash
cd worker && python -c "from sandbox.manager import SandboxManager; from sandbox.docker_backend import DockerBackend; from sandbox.exceptions import SandboxError; print('Imports OK')"
```

**Expected**: Imports OK

### Level 3: Unit Tests

```bash
cd worker && uv run pytest tests/test_docker_backend.py tests/test_sandbox_manager.py -v
```

**Expected**: All tests pass

### Level 4: Docker Image Build

```bash
cd docker/sandbox-base && docker build -t badgers-sandbox:latest .
```

**Expected**: Image builds successfully

### Level 5: Integration Test (Optional)

```bash
cd worker && uv run pytest tests/test_sandbox_integration.py -v --docker
```

**Expected**: All integration tests pass (requires Docker daemon)

---

## ACCEPTANCE CRITERIA

- [ ] DockerBackend class created with all lifecycle methods
- [ ] SandboxManager class created with async context manager support
- [ ] Custom exceptions defined for sandbox operations
- [ ] Base Docker image enhanced with Node.js and security hardening
- [ ] Database integration working (create SandboxSession, update terminated_at)
- [ ] Resource limits enforced (CPU, memory)
- [ ] Proper cleanup on success and failure
- [ ] Unit tests pass with mocked Docker SDK
- [ ] Docker image builds successfully
- [ ] All linting checks pass
- [ ] Code follows project conventions

---

## COMPLETION CHECKLIST

- [ ] exceptions.py created
- [ ] docker_backend.py created
- [ ] manager.py created
- [ ] Dockerfile updated
- [ ] test_docker_backend.py created
- [ ] test_sandbox_manager.py created
- [ ] All validation commands pass
- [ ] Linting clean
- [ ] Unit tests pass
- [ ] Docker image builds

---

## NOTES

**Design Decisions:**

1. **Separation of Concerns**: DockerBackend handles Docker SDK operations, SandboxManager handles orchestration and database integration. This allows testing each layer independently.

2. **Async Context Manager**: SandboxManager implements `__aenter__` and `__aexit__` to ensure cleanup happens automatically, even on exceptions.

3. **Resource Limits**: Enforced at container creation time using Docker SDK parameters (mem_limit, cpu_quota). Default limits: 512MB memory, 50% CPU.

4. **Ephemeral Containers**: Containers are created per TaskRun and destroyed after use. No container reuse to ensure isolation.

5. **Database Integration**: SandboxSession tracks container_id, image, and resource limits. The terminated_at field is set during cleanup.

**Implementation Order Rationale:**

- Exceptions first (needed by other modules)
- DockerBackend second (low-level operations)
- SandboxManager third (high-level orchestration)
- Dockerfile update (can be done in parallel)
- Tests last (verify functionality)

**Security Considerations:**

- Non-root user in Docker image
- Resource limits prevent resource exhaustion
- Network isolation (bridge mode by default)
- No privileged containers
- Containers destroyed after use (no data persistence)

**Future Considerations:**

- Container pooling for performance (reuse containers)
- Volume mounting for project files
- Network policies for internet access control
- Container health checks
- Timeout enforcement for long-running commands
- Log streaming for real-time output

**Known Limitations:**

- Requires Docker daemon running on worker host
- No Windows container support (Linux containers only)
- Resource limits are soft limits (Docker enforces)
- No GPU support in MVP

**Testing Notes:**

- Unit tests use mocks to avoid Docker daemon dependency
- Integration tests require Docker daemon (optional)
- CI/CD should use mocked tests only
- Local development can run integration tests
