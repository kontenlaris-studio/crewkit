"""State store module: atomic JSON-based state persistence."""

import json
import os
import tempfile
from typing import Any, Dict


class StateStore:
    """
    JSON-based state store with atomic writes.
    
    Reads from file; missing or corrupt files load as empty dict.
    Writes are atomic: temp file + os.replace.
    """
    
    def __init__(self, path: str) -> None:
        """Initialize store with a file path."""
        self.path = path
        self._data: Dict[str, Any] = {}
        self._load()
    
    def _load(self) -> None:
        """Load state from file. Corrupt files load as empty dict."""
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r') as f:
                    loaded = json.load(f)
                    if isinstance(loaded, dict):
                        self._data = loaded
            except (json.JSONDecodeError, IOError):
                # Corrupt file; use empty state
                self._data = {}
        else:
            self._data = {}
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from state."""
        return self._data.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set a value in state (in memory)."""
        self._data[key] = value
    
    def __getitem__(self, key: str) -> Any:
        """Dict-like get."""
        return self._data[key]
    
    def __setitem__(self, key: str, value: Any) -> None:
        """Dict-like set."""
        self._data[key] = value
    
    def __contains__(self, key: str) -> bool:
        """Check if key exists."""
        return key in self._data
    
    def save(self) -> None:
        """
        Atomically save state to file.
        Uses temp file + os.replace to ensure atomicity.
        """
        # Create temp file in same directory to ensure same filesystem
        dir_path = os.path.dirname(self.path) or '.'
        
        with tempfile.NamedTemporaryFile(
            mode='w',
            dir=dir_path,
            delete=False,
            suffix='.tmp'
        ) as tmp:
            json.dump(self._data, tmp)
            tmp_path = tmp.name
        
        # Atomic replace
        try:
            os.replace(tmp_path, self.path)
        except Exception:
            # Clean up temp file on error
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
    
    def to_dict(self) -> Dict[str, Any]:
        """Get a copy of all state."""
        return dict(self._data)
