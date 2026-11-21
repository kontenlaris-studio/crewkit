# Telegram Task Reminder Bot

A task-reminder bot built on CrewKit. Stores tasks in state, checks for due tasks, and sends reminders. Polls Telegram for commands when a bot token is provided.

## Features

- **Task Management**: Add tasks with due times, list all tasks, mark tasks as done.
- **Automatic Reminders**: Scheduler checks due tasks and sends notifications.
- **Telegram Integration**: Polls Telegram for `/add`, `/list`, and `/done` commands (when BOT_TOKEN is set).
- **Offline Demo Mode**: Run with `--demo` flag to see tasks and reminders without any tokens or network.

## Commands

- `/add <title> | <minutes>` — Add a task due in N minutes.
- `/list` — Show all tasks.
- `/done <id>` — Mark task #id as done.

## Usage

### Demo Mode (offline, no setup needed)

```bash
python3 bot.py --demo
```

This runs with `demo.json`: 3 sample tasks, one already due. You will see the reminder notification printed.

### Normal Mode (requires config)

1. Create a `config.json`:
   ```json
   {
     "bot_token": "YOUR_TELEGRAM_BOT_TOKEN",
     "chat_id": "YOUR_CHAT_ID"
   }
   ```

2. Run:
   ```bash
   python3 bot.py --config config.json --state state.json
   ```

The bot will poll Telegram every 5 seconds and write state to `state.json`.

## Demo Data

`demo.json` contains:
- 3 sample tasks: "Buy groceries" (due in 30m), "Call mother" (due in 2h), "Review code" (already due).
- Fake clock set to `2024-01-01T12:00:00Z`.

When you run `--demo`, you should see a reminder notification for the "Review code" task.

## Files

- `bot.py` — Main bot application.
- `demo.json` — Sample data for demo mode.
- `config.json` — Configuration (create this for normal operation).
- `state.json` — State file (auto-created during operation).
