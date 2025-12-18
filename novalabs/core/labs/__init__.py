"""
NovaLabs Core Labs - Logic layer for lab execution.

The BaseLab class provides state management, progress tracking, and lifecycle
hooks that can be overridden for custom lab behavior.
"""

from .base import BaseLab

__all__ = [
    'BaseLab',
]
