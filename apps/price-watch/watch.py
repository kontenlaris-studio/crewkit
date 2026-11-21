#!/usr/bin/env python3
"""Price-watch notifier using CrewKit."""

import sys
import os
import json
import time
import argparse
import re
import urllib.request
import urllib.error
from typing import Dict, List, Any, Optional

# Bootstrap sys.path to import crewkit from core
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../core'))

from crewkit import (
    Config, load_config,
    now_iso,
    StateStore,
    Notifier, ConsoleSink,
    run_loop
)


class PriceExtractor:
    """Extract prices from HTML using JSON-LD first, then regex fallback."""
    
    @staticmethod
    def extract_from_json_ld(html: str) -> Optional[float]:
        """Extract price from JSON-LD schema (price field)."""
        try:
            # Find JSON-LD blocks
            pattern = r'<script\s+type=["\']application/ld\+json["\']>(.*?)</script>'
            matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
            
            for match in matches:
                try:
                    data = json.loads(match)
                    if isinstance(data, dict):
                        price = data.get('price')
                        if price is not None:
                            if isinstance(price, str):
                                # Try to parse as number
                                return float(price)
                            elif isinstance(price, (int, float)):
                                return float(price)
                        
                        # Check nested structures
                        offers = data.get('offers')
                        if isinstance(offers, dict):
                            price = offers.get('price')
                            if price is not None:
                                if isinstance(price, str):
                                    return float(price)
                                elif isinstance(price, (int, float)):
                                    return float(price)
                        elif isinstance(offers, list):
                            for offer in offers:
                                if isinstance(offer, dict):
                                    price = offer.get('price')
                                    if price is not None:
                                        if isinstance(price, str):
                                            return float(price)
                                        elif isinstance(price, (int, float)):
                                            return float(price)
                except (json.JSONDecodeError, ValueError, TypeError):
                    continue
        except Exception:
            pass
        
        return None
    
    @staticmethod
    def extract_from_regex(html: str) -> Optional[float]:
        """Fallback: extract price from HTML using regex patterns."""
        try:
            # Common patterns: $12.99, €50, £25.00, "price": 99.99
            patterns = [
                r'["\']?price["\']?\s*:\s*["\']?(\d+\.?\d*)',  # price: 99
                r'["\']?price["\']?\s*[=:]\s*["\']?(\d+\.?\d*)',  # price=99 or price: 99
                r'[$£€]\s*(\d+\.?\d*)',  # $99 or £99 or €99
                r'(\d+\.?\d*)\s*[uU][sS][dD]',  # 99 USD
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, html, re.IGNORECASE)
                if matches:
                    try:
                        return float(matches[0])
                    except ValueError:
                        continue
        except Exception:
            pass
        
        return None
    
    @staticmethod
    def extract(html: str) -> Optional[float]:
        """Extract price from HTML (JSON-LD first, then regex)."""
        # Try JSON-LD first
        price = PriceExtractor.extract_from_json_ld(html)
        if price is not None:
            return price
        
        # Fallback to regex
        return PriceExtractor.extract_from_regex(html)


class PriceWatcher:
    """Price watcher: monitors prices and sends alerts."""
    
    def __init__(self, config: Config, store: StateStore, notifier: Notifier, fake_fetcher=None):
        """Initialize watcher.
        
        Args:
            config: Config instance
            store: StateStore for watchlist persistence
            notifier: Notifier for sending alerts
            fake_fetcher: optional function(url) -> html (for testing)
        """
        self.config = config
        self.store = store
        self.notifier = notifier
        self.fake_fetcher = fake_fetcher
    
    def get_watchlist(self) -> List[Dict[str, Any]]:
        """Get watchlist from state."""
        state = self.store.to_dict()
        watchlist = state.get('watchlist', [])
        if not isinstance(watchlist, list):
            watchlist = []
        return watchlist
    
    def set_watchlist(self, watchlist: List[Dict[str, Any]]) -> None:
        """Save watchlist to state."""
        self.store['watchlist'] = watchlist
        self.store.save()
    
    def add_watch(self, name: str, url: str, target_price: float) -> None:
        """Add an item to the watchlist."""
        watchlist = self.get_watchlist()
        watch = {
            'id': len(watchlist),
            'name': name,
            'url': url,
            'target_price': target_price,
            'alerted': False
        }
        watchlist.append(watch)
        self.set_watchlist(watchlist)
    
    def fetch_url(self, url: str) -> Optional[str]:
        """Fetch URL and return HTML (5s timeout)."""
        if self.fake_fetcher:
            return self.fake_fetcher(url)
        
        try:
            req = urllib.request.Request(url, method='GET')
            with urllib.request.urlopen(req, timeout=5) as response:
                return response.read().decode('utf-8', errors='ignore')
        except (urllib.error.URLError, urllib.error.HTTPError, Exception):
            return None
    
    def check_prices(self) -> None:
        """Check all watched items for price alerts."""
        watchlist = self.get_watchlist()
        now = now_iso()
        
        for item in watchlist:
            if item.get('alerted'):
                continue
            
            url = item.get('url')
            name = item.get('name', 'Item')
            target = item.get('target_price')
            
            if not url or target is None:
                continue
            
            # Fetch page
            html = self.fetch_url(url)
            if not html:
                continue
            
            # Extract price
            price = PriceExtractor.extract(html)
            if price is None:
                continue
            
            # Check if price is at or below target
            if price <= target:
                self.notifier.notify(
                    title=f"Price Alert: {name}",
                    body=f"Price ${price} <= target ${target}",
                    timestamp=now
                )
                item['alerted'] = True
        
        self.set_watchlist(watchlist)


def demo_mode() -> None:
    """Run in demo mode: load demo.json with embedded HTML."""
    import tempfile
    
    demo_path = os.path.join(os.path.dirname(__file__), 'demo.json')
    
    if not os.path.exists(demo_path):
        print("Error: demo.json not found.")
        sys.exit(1)
    
    with open(demo_path, 'r') as f:
        demo = json.load(f)
    
    # Extract demo data
    config_data = demo.get('config', {})
    initial_state = demo.get('state', {})
    pages = demo.get('pages', {})  # Embedded HTML pages by URL
    fake_time = demo.get('fake_time', '2024-01-01T12:00:00Z')
    
    # Create fake clock
    def fake_now():
        return fake_time
    
    # Create fake fetcher that returns embedded HTML
    def fake_fetcher(url):
        return pages.get(url)
    
    # Create instances
    config = Config(data=config_data)
    
    # Use temporary state store for demo (not persistent)
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as tmp:
        temp_store_path = tmp.name
    
    try:
        store = StateStore(temp_store_path)
        # Directly set initial state
        for key, value in initial_state.items():
            store[key] = value
        
        notifications = []
        class DemoSink:
            def send(self, message):
                notifications.append(message)
                print(message)
        
        notifier = Notifier([DemoSink()])
        
        # Create watcher and run (note: watcher doesn't use fake clock, only for consistency)
        watcher = PriceWatcher(config, store, notifier, fake_fetcher=fake_fetcher)
        watcher.check_prices()
        
        print("Demo completed.")
    finally:
        # Clean up temp file
        try:
            os.unlink(temp_store_path)
        except OSError:
            pass


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Price-watch notifier.')
    parser.add_argument('--demo', action='store_true', help='Run in demo mode (offline)')
    parser.add_argument('--config', default='config.json', help='Config file path')
    parser.add_argument('--state', default='state.json', help='State file path')
    
    args = parser.parse_args()
    
    if args.demo:
        demo_mode()
        return 0
    
    # Load config and state
    config = load_config(args.config)
    store = StateStore(args.state)
    
    # Set up notifier
    notifier = Notifier([ConsoleSink()])
    
    # Create watcher
    watcher = PriceWatcher(config, store, notifier)
    
    # Define scheduler job
    jobs = {
        'check_prices': watcher.check_prices
    }
    
    # Run loop
    print("Price watcher started. Press Ctrl+C to stop.")
    try:
        while True:
            result = run_loop(jobs, store, notifier, ticks=1)
            time.sleep(60)  # Check every 60 seconds
    except KeyboardInterrupt:
        print("\nPrice watcher stopped.")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
