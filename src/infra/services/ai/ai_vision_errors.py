"""
Vision error types for the infra AI layer.

Shim: canonical definitions live in the domain layer so the app layer can import
them without crossing the app→infra boundary.
"""

from src.domain.exceptions.ai_exceptions import AIVisionError, AIVisionFailureKind

__all__ = ["AIVisionError", "AIVisionFailureKind"]
