"""Custom exceptions for sandbox operations."""


class SandboxError(Exception):
    """Base exception for sandbox operations."""
    pass


class SandboxCreationError(SandboxError):
    """Failed to create sandbox."""
    pass


class SandboxExecutionError(SandboxError):
    """Failed to execute command in sandbox."""
    pass


class SandboxCleanupError(SandboxError):
    """Failed to cleanup sandbox."""
    pass


class SandboxPoolExhaustedError(SandboxError):
    """No reusable sandbox is currently available."""
    pass


class SandboxHealthCheckError(SandboxError):
    """Sandbox failed post-reset health validation."""
    pass
