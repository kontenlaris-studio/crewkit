"""Notifier module: fan out messages to multiple sinks."""

import json
import urllib.request
import urllib.error
from typing import Any, List, Protocol


class Sink(Protocol):
    """Protocol for notification sinks."""
    
    def send(self, message: str) -> None:
        """Send a formatted message."""
        ...


class ConsoleSink:
    """Sink that prints to stdout."""
    
    def send(self, message: str) -> None:
        """Print message to stdout."""
        print(message)


class FileSink:
    """Sink that appends to a log file."""
    
    def __init__(self, path: str) -> None:
        """Initialize with file path."""
        self.path = path
    
    def send(self, message: str) -> None:
        """Append message to file."""
        try:
            with open(self.path, 'a') as f:
                f.write(message + '\n')
        except IOError:
            # Silently fail if file cannot be written
            pass


class WebhookSink:
    """Sink that sends messages to a webhook URL via HTTP POST."""
    
    def __init__(self, url: str, timeout: float = 5.0) -> None:
        """
        Initialize with webhook URL.
        
        Args:
            url: HTTP(S) endpoint to POST to
            timeout: request timeout in seconds
        """
        self.url = url
        self.timeout = timeout
    
    def send(self, message: str) -> None:
        """
        Send message to webhook (best-effort, never raises).
        Posts JSON: {message: "<message>"}
        """
        try:
            payload = json.dumps({"message": message}).encode('utf-8')
            req = urllib.request.Request(
                self.url,
                data=payload,
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as _:
                pass
        except (urllib.error.URLError, urllib.error.HTTPError, Exception):
            # Best-effort: silently fail on any network or parsing error
            pass


class Notifier:
    """Notifies via multiple sinks."""
    
    def __init__(self, sinks: List[Sink] | None = None) -> None:
        """
        Initialize with a list of sinks.
        
        Args:
            sinks: list of sink objects (ConsoleSink, FileSink, WebhookSink, etc.)
        """
        self.sinks = sinks or []
    
    def notify(self, title: str, body: str = "", timestamp: str = "") -> None:
        """
        Notify all sinks with a formatted message.
        
        Format: [ISO] title — body
        where ISO is the timestamp.
        
        Args:
            title: notification title
            body: notification body (optional)
            timestamp: ISO-8601 timestamp (required for format)
        """
        if body:
            message = f"[{timestamp}] {title} — {body}"
        else:
            message = f"[{timestamp}] {title}"
        
        for sink in self.sinks:
            sink.send(message)
