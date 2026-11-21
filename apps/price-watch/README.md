# Price Watch Notifier

A price-watch notifier built on CrewKit. Monitors URLs for prices and sends alerts when prices drop to or below targets.

## Features

- **Price Monitoring**: Watch product pages for price changes.
- **Smart Price Extraction**: Uses JSON-LD schema first, falls back to regex patterns for common price formats.
- **Price Alerts**: Notifies when price ≤ target.
- **Offline Demo Mode**: Run with `--demo` flag to see alerts without network.

## Price Extraction

The watcher extracts prices from HTML in two ways:

1. **JSON-LD Schema** (preferred): Looks for `<script type="application/ld+json">` with a `price` field.
2. **Regex Fallback**: Searches for patterns like `$99.99`, `€50`, `£25`, or `"price": 99`.

## Usage

### Demo Mode (offline, no setup needed)

```bash
python3 watch.py --demo
```

This runs with `demo.json`: watches 2 items with embedded HTML. One item (Widget at $45.99) is below target ($50), so you will see a price alert.

### Normal Mode (requires config and network)

1. Create `config.json` (can be empty for basic operation):
   ```json
   {}
   ```

2. Create `state.json` with a watchlist:
   ```json
   {
     "watchlist": [
       {
         "id": 0,
         "name": "My Widget",
         "url": "https://shop.example.com/widget",
         "target_price": 50.0,
         "alerted": false
       }
     ]
   }
   ```

3. Run:
   ```bash
   python3 watch.py --config config.json --state state.json
   ```

The watcher will check prices every 60 seconds.

## Demo Data

`demo.json` contains:
- **Widget**: JSON-LD schema with price $45.99 (below $50 target) → alert fires.
- **Gadget**: Regex pattern with price $120 (above $100 target) → no alert.

When you run `--demo`, you should see one price alert for the Widget.

## Files

- `watch.py` — Main watcher application.
- `demo.json` — Sample data with embedded HTML for demo mode.
- `config.json` — Configuration (create this for normal operation).
- `state.json` — State file with watchlist (auto-created during operation).
