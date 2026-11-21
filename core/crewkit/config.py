"""Config module: loads JSON configuration with environment variable overrides."""

import json
import os
from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class Config:
    """Configuration container. Attributes can be accessed as dict-like or by name."""
    data: Dict[str, Any]

    def get(self, key: str, default: Any = None) -> Any:
        """Get a config value by key."""
        return self.data.get(key, default)

    def __getitem__(self, key: str) -> Any:
        """Dict-like access."""
        return self.data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        """Dict-like setting."""
        self.data[key] = value


def load_config(path: str, defaults: Dict[str, Any] | None = None) -> Config:
    """
    Load JSON config from path with optional defaults.
    
    Missing file yields defaults (or empty dict if no defaults given).
    Keys may be overridden by CREWKIT_<KEY> environment variables.
    Environment variable values are parsed as JSON if possible, otherwise treated as strings.
    """
    if defaults is None:
        defaults = {}
    
    config_data = dict(defaults)
    
    # Try to load from file
    if os.path.exists(path):
        try:
            with open(path, 'r') as f:
                file_data = json.load(f)
                if isinstance(file_data, dict):
                    config_data.update(file_data)
        except (json.JSONDecodeError, IOError):
            # File exists but is corrupt; use defaults
            pass
    
    # Apply environment variable overrides (CREWKIT_<KEY>)
    for key, value in os.environ.items():
        if key.startswith('CREWKIT_'):
            config_key = key[8:].lower()  # Strip 'CREWKIT_' and lowercase
            # Try to parse as JSON, fall back to string
            try:
                config_data[config_key] = json.loads(value)
            except json.JSONDecodeError:
                config_data[config_key] = value
    
    return Config(data=config_data)
