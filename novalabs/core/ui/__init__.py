"""
Base UI components for NovaLabs labs.

The BaseLabUI class provides a fully functional default UI for labs.
Custom labs can subclass BaseLabUI to override specific rendering methods.

The resolver module handles dynamic loading of UI classes based on
lab.toml configuration or convention.
"""

from .base import BaseLabUI
from .resolver import resolve_ui_class, import_class, get_ui_class_for_lab

__all__ = [
    'BaseLabUI',
    'resolve_ui_class',
    'import_class',
    'get_ui_class_for_lab',
]
