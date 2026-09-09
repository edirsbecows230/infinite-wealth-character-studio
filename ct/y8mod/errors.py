"""Typed failures used instead of optimization-sensitive assertions."""


class Y8ProjectError(RuntimeError):
    """Base class for expected command failures."""


class ValidationError(Y8ProjectError):
    """An input or artifact failed a required invariant."""


class SafetyError(Y8ProjectError):
    """A requested operation cannot be performed safely."""

