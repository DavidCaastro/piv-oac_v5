"""sdk/engram — Read-only, role-scoped engram access layer."""

from .reader import EngramAccessError, EngramReader

__all__ = ["EngramAccessError", "EngramReader"]
