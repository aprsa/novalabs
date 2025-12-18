"""
UI class resolver for NovaLabs labs.

Resolves which UI class to use for a lab at runtime:
1. Explicit declaration in lab.toml [ui].class
2. Convention: {lab_dir}/ui.py with {PascalSlug}Lab class
3. Default: BaseLabUI

This module is intentionally separate from content/discovery.py to keep
UI concerns out of the content loading layer.
"""

import ast
import importlib
import logging
import re
from pathlib import Path
from typing import Optional, Type, TYPE_CHECKING

import toml

if TYPE_CHECKING:
    from .base import BaseLabUI
    from ..content.schemas import LabConfig

logger = logging.getLogger(__name__)

# Default UI class path
DEFAULT_UI_CLASS = "novalabs.core.ui.base:BaseLabUI"


def slug_to_pascal(slug: str) -> str:
    """
    Convert a slug to PascalCase.
    
    Examples:
        celestial-sphere → CelestialSphere
        celestial_sphere → CelestialSphere
        my-awesome-lab → MyAwesomeLab
    
    Args:
        slug: Slug string with hyphens or underscores
        
    Returns:
        PascalCase string
    """
    # Replace hyphens and underscores with spaces, then title case, then remove spaces
    words = re.split(r'[-_]', slug)
    return ''.join(word.capitalize() for word in words)


def _class_exists_in_file(file_path: Path, class_name: str) -> bool:
    """
    Check if a class with the given name exists in a Python file.
    
    Uses AST parsing to avoid importing the module.
    
    Args:
        file_path: Path to the Python file
        class_name: Name of the class to look for
        
    Returns:
        True if the class exists
    """
    try:
        source = file_path.read_text(encoding='utf-8')
        tree = ast.parse(source)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                return True
        
        return False
    except Exception as e:
        logger.warning(f"Could not parse {file_path}: {e}")
        return False


def _build_module_path(lab_path: Path) -> str:
    """
    Build a Python module path from a lab directory path.
    
    Handles both bundled labs (novalabs/labs/...) and user labs (~/.novalabs/labs/...).
    
    Args:
        lab_path: Path to the lab directory
        
    Returns:
        Dotted module path (e.g., 'novalabs.labs.celestial_sphere')
    """
    # Check if this is a bundled lab (under novalabs package)
    parts = lab_path.parts
    
    # Look for 'novalabs' in the path
    if 'novalabs' in parts:
        novalabs_idx = parts.index('novalabs')
        # Build path from novalabs onwards
        module_parts = parts[novalabs_idx:]
        return '.'.join(module_parts)
    
    # For user labs, we need to add them to sys.path dynamically
    # Return a special marker that import_class will handle
    return f"__user_lab__:{lab_path}"


def resolve_ui_class(
    lab_path: Path,
    config: Optional['LabConfig'] = None
) -> str:
    """
    Resolve the UI class path for a lab.
    
    Resolution order:
    1. Explicit [ui].class declaration in lab.toml
    2. Convention-based: {lab_dir}/ui.py with {PascalSlug}Lab class
    3. Default: BaseLabUI
    
    Args:
        lab_path: Path to the lab directory
        config: Optional pre-loaded LabConfig (loaded from TOML if not provided)
        
    Returns:
        Class path string (e.g., 'novalabs.labs.mylab.ui:MyLabUI')
    """
    content_dir = lab_path / 'content'
    
    # Load config if not provided
    if config is None:
        lab_toml = content_dir / 'lab.toml'
        if lab_toml.exists():
            try:
                raw = toml.load(lab_toml)
                # Import here to avoid circular imports
                from ..content.schemas import LabConfig
                config = LabConfig(**raw)
            except Exception as e:
                logger.warning(f"Could not load lab.toml for {lab_path}: {e}")
    
    # Priority 1: Explicit declaration in TOML
    if config and hasattr(config, 'ui') and config.ui and config.ui.class_path:
        logger.debug(f"Using explicit UI class for {lab_path.name}: {config.ui.class_path}")
        return config.ui.class_path
    
    # Priority 2: Convention-based discovery
    ui_py = lab_path / 'ui.py'
    if ui_py.exists():
        slug = config.lab.slug if config else lab_path.name
        class_name = slug_to_pascal(slug) + 'Lab'
        
        if _class_exists_in_file(ui_py, class_name):
            module_path = _build_module_path(lab_path)
            
            if module_path.startswith('__user_lab__:'):
                # User lab - return special path for import_class to handle
                class_path = f"__user_lab__:{ui_py}:{class_name}"
            else:
                # Bundled lab - standard module path
                class_path = f"{module_path}.ui:{class_name}"
            
            logger.debug(f"Using convention UI class for {lab_path.name}: {class_path}")
            return class_path
        else:
            logger.debug(f"ui.py exists for {lab_path.name} but class {class_name} not found")
    
    # Priority 3: Default
    logger.debug(f"Using default BaseLabUI for {lab_path.name}")
    return DEFAULT_UI_CLASS


def import_class(class_path: str) -> Type['BaseLabUI']:
    """
    Import and return a class from a module:class path string.
    
    Handles both standard module paths and user lab paths.
    
    Args:
        class_path: Path in format 'module.path:ClassName' or 
                    '__user_lab__:/path/to/ui.py:ClassName'
    
    Returns:
        The class object
        
    Raises:
        ImportError: If the module or class cannot be found
        AttributeError: If the class doesn't exist in the module
    """
    # Handle user lab special path
    if class_path.startswith('__user_lab__:'):
        _, file_path, class_name = class_path.split(':', 2)
        return _import_from_file(Path(file_path), class_name)
    
    # Standard module:class format
    if ':' not in class_path:
        raise ValueError(f"Invalid class path format: {class_path}. Expected 'module.path:ClassName'")
    
    module_path, class_name = class_path.rsplit(':', 1)
    
    try:
        module = importlib.import_module(module_path)
        return getattr(module, class_name)
    except ImportError as e:
        raise ImportError(f"Could not import module '{module_path}': {e}") from e
    except AttributeError as e:
        raise AttributeError(f"Class '{class_name}' not found in module '{module_path}'") from e


def _import_from_file(file_path: Path, class_name: str) -> Type['BaseLabUI']:
    """
    Import a class directly from a Python file.
    
    Used for user-installed labs that aren't on the Python path.
    
    Args:
        file_path: Path to the Python file
        class_name: Name of the class to import
        
    Returns:
        The class object
    """
    import importlib.util
    
    spec = importlib.util.spec_from_file_location("_user_lab_ui", file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module spec from {file_path}")
    
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    if not hasattr(module, class_name):
        raise AttributeError(f"Class '{class_name}' not found in {file_path}")
    
    return getattr(module, class_name)


def get_ui_class_for_lab(lab_path: Path) -> Type['BaseLabUI']:
    """
    Convenience function to resolve and import UI class in one call.
    
    Args:
        lab_path: Path to the lab directory
        
    Returns:
        The UI class object ready for instantiation
    """
    class_path = resolve_ui_class(lab_path)
    return import_class(class_path)
