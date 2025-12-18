"""
Configuration management for NovaLabs.

Loads configuration from TOML files and environment variables.
"""

import os
from pathlib import Path
from typing import Optional
import toml


class NovaLabsConfig:
    """
    Singleton configuration manager for NovaLabs.

    Loads configuration from TOML files and environment variables.
    """

    _instance = None
    _data: Optional[dict] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @staticmethod
    def _find_config_file() -> Path:
        """
        Find the configuration file.

        Search order:
        1. NOVALABS_CONFIG environment variable
        2. {project_root}/config.toml (top-level directory)
        3. ~/.novalabs/config.toml (user config)
        """

        # Environment variable
        if env_path := os.environ.get('NOVALABS_CONFIG'):
            path = Path(env_path)
            if path.exists():
                return path
            raise FileNotFoundError(f"Config file not found: {env_path}")

        # Project root directory
        project_root = NovaLabsConfig._get_project_root()
        if (project_root / 'config.toml').exists():
            return project_root / 'config.toml'

        # User config
        user_config = Path.home() / '.novalabs' / 'config.toml'
        if user_config.exists():
            return user_config

        raise FileNotFoundError(
            "No config file found. Set NOVALABS_CONFIG or create config.toml"
        )

    @staticmethod
    def _get_project_root() -> Path:
        """
        Get the project root directory by searching upwards for pyproject.toml.
        If it fails to find it, it defaults to three levels up from this file.
        """
        current = Path(__file__).resolve().parent

        while current != current.parent:
            if (current / 'pyproject.toml').exists():
                return current
            current = current.parent

        # Fallback: three levels up from this file
        return Path(__file__).parent.parent.parent

    @staticmethod
    def _apply_env_overrides(config: dict) -> None:
        """Apply environment variable overrides to config."""

        # Database URL override
        if db_url := os.environ.get('NOVALABS_DATABASE_URL'):
            config.setdefault('database', {})['url'] = db_url

        # Debug mode override
        if debug := os.environ.get('NOVALABS_DEBUG'):
            config['debug'] = debug.lower() in ('true', '1', 'yes')

        # Labs directory override
        if labs_dir := os.environ.get('NOVALABS_LABS_DIR'):
            config.setdefault('labs', {})['directory'] = labs_dir

    def load(self, config_path: Optional[Path] = None) -> dict:
        """
        Load configuration from TOML file.

        Args:
            config_path: Optional explicit path to config file.
                         If None, searches default locations.

        Returns:
            Configuration dictionary.
        """
        if config_path is None:
            config_path = self._find_config_file()

        self._data = toml.load(config_path)
        self._apply_env_overrides(self._data)

        return self._data

    @property
    def data(self) -> dict:
        """
        Get the current configuration data.

        Loads config if not already loaded.
        """
        if self._data is None:
            self.load()
        assert self._data is not None  # Type narrowing
        return self._data

    def get_database_url(self) -> str:
        """Get the database URL from config, resolving relative paths."""
        url = self.data.get('database', {}).get('url', 'sqlite://data/novalabs.db')

        # If it's a relative SQLite path, make it absolute relative to project root
        if url.startswith('sqlite://') and not url.startswith('sqlite:///'):
            # Extract the path part (after sqlite://)
            db_path = url[9:]  # len('sqlite://') = 9
            if not db_path.startswith('/'):
                # Relative path - make absolute relative to project root
                project_root = self._get_project_root()
                abs_path = project_root / db_path
                # Use sqlite:// for Tortoise (it handles paths differently than SQLAlchemy)
                url = f'sqlite://{abs_path}'

        return url

    def get_labs_directory(self) -> Path:
        """Get the labs directory path."""
        labs_dir = self.data.get('labs', {}).get('directory')

        if labs_dir:
            return Path(labs_dir)

        # Default: relative to this package
        return Path(__file__).parent.parent / 'labs'

    def is_debug(self) -> bool:
        """Check if debug mode is enabled."""
        return self.data.get('debug', False)
