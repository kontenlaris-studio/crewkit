#!/usr/bin/env python3
"""Telegram task-reminder bot using CrewKit."""

import sys
import os
import json
import time
import argparse
import urllib.request
import urllib.error
import tempfile
from typing import Dict, List, Any

# Bootstrap sys.path to import crewkit from core
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../core'))

from crewkit import (
    Config, load_config,
    now_iso, parse_iso,
    StateStore,
    Notifier, ConsoleSink,
    run_loop
)


class TelegramBotError(Exception):
    """Raised when Telegram API fails."""
    pass


class TaskReminder:
    """Task reminder bot: stores tasks, tracks reminders, polls Telegram."""
    
    def __init__(self, config: Config, store: StateStore, notifier: Notifier, fake_clock=None):
        """Initialize bot with config, state store, and notifier.
        
        Args:
            config: Config instance (expects bot_token, chat_id)
            store: StateStore for task persistence
            notifier: Notifier for sending reminders
            fake_clock: optional function returning ISO-8601 time (for testing)
        """
        self.config = config
        self.store = store
        self.notifier = notifier
        self.fake_clock = fake_clock or now_iso
        self.offset = 0  # For Telegram long-polling
    
    def get_tasks(self) -> List[Dict[str, Any]]:
        """Get all tasks from state."""
        state = self.store.to_dict()
        tasks = state.get('tasks', [])
        if not isinstance(tasks, list):
            tasks = []
        return tasks
    
    def set_tasks(self, tasks: List[Dict[str, Any]]) -> None:
        """Save tasks to state."""
        self.store['tasks'] = tasks
        self.store.save()
    
    def add_task(self, title: str, due_minutes: int) -> None:
        """Add a new task with due time in minutes from now."""
        tasks = self.get_tasks()
        
        # Parse current time and add minutes
        now_dt = parse_iso(self.fake_clock())
        from datetime import timedelta
        due_dt = now_dt + timedelta(minutes=due_minutes)
        due_iso = due_dt.isoformat(timespec='seconds').replace('+00:00', 'Z')
        
        task = {
            'id': len(tasks),  # Simple ID generation
            'title': title,
            'due_iso': due_iso,
            'reminded': False
        }
        tasks.append(task)
        self.set_tasks(tasks)
    
    def list_tasks(self) -> str:
        """Return a formatted list of all tasks."""
        tasks = self.get_tasks()
        if not tasks:
            return "No tasks."
        
        lines = []
        for task in tasks:
            task_id = task.get('id', '?')
            title = task.get('title', '?')
            due = task.get('due_iso', '?')
            reminded = '✓' if task.get('reminded') else '○'
            lines.append(f"[{reminded}] #{task_id}: {title} — due {due}")
        
        return '\n'.join(lines)
    
    def mark_done(self, task_id: int) -> str:
        """Mark task as done and return status message."""
        tasks = self.get_tasks()
        for task in tasks:
            if task.get('id') == task_id:
                tasks.remove(task)
                self.set_tasks(tasks)
                return f"Task #{task_id} done."
        return f"Task #{task_id} not found."
    
    def check_due_tasks(self) -> None:
        """Check for due tasks and send reminders."""
        tasks = self.get_tasks()
        now = self.fake_clock()
        now_dt = parse_iso(now)
        
        for task in tasks:
            if task.get('reminded'):
                continue
            
            due_str = task.get('due_iso')
            if not due_str:
                continue
            
            try:
                due_dt = parse_iso(due_str)
                if now_dt >= due_dt:
                    # Task is due, send reminder
                    title = task.get('title', 'Task')
                    self.notifier.notify(
                        title=f"Reminder: {title}",
                        body=f"Task due at {due_str}",
                        timestamp=now
                    )
                    task['reminded'] = True
            except (ValueError, TypeError):
                # Corrupt due_iso, skip
                pass
        
        self.set_tasks(tasks)
    
    def get_updates(self) -> List[Dict[str, Any]]:
        """Fetch updates from Telegram (only if BOT_TOKEN is set)."""
        bot_token = self.config.get('bot_token')
        if not bot_token:
            return []
        
        try:
            url = f"https://api.telegram.org/bot{bot_token}/getUpdates?offset={self.offset}&timeout=1"
            req = urllib.request.Request(url, method='GET')
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode('utf-8'))
                if data.get('ok'):
                    updates = data.get('result', [])
                    if updates:
                        self.offset = updates[-1]['update_id'] + 1
                    return updates
        except (urllib.error.URLError, urllib.error.HTTPError, Exception):
            # Network error or invalid response
            pass
        
        return []
    
    def send_message(self, chat_id: str, text: str) -> None:
        """Send a message to Telegram (only if BOT_TOKEN is set)."""
        bot_token = self.config.get('bot_token')
        if not bot_token:
            return
        
        try:
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = json.dumps({'chat_id': chat_id, 'text': text}).encode('utf-8')
            req = urllib.request.Request(
                url,
                data=payload,
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=5) as _:
                pass
        except (urllib.error.URLError, urllib.error.HTTPError, Exception):
            # Network error; best-effort, do not raise
            pass
    
    def handle_command(self, chat_id: str, text: str) -> str:
        """Parse and handle a command, return response."""
        text = text.strip()
        
        if text.startswith('/add '):
            # Parse: /add <title> | <minutes>
            rest = text[5:].strip()
            if '|' in rest:
                title, mins_str = rest.split('|', 1)
                title = title.strip()
                try:
                    minutes = int(mins_str.strip())
                    self.add_task(title, minutes)
                    return f"Task '{title}' added (due in {minutes}m)."
                except ValueError:
                    return "Invalid format. Use: /add <title> | <minutes>"
            else:
                return "Invalid format. Use: /add <title> | <minutes>"
        
        elif text == '/list':
            return self.list_tasks()
        
        elif text.startswith('/done '):
            # Parse: /done <id>
            try:
                task_id = int(text[6:].strip())
                return self.mark_done(task_id)
            except ValueError:
                return "Invalid task ID."
        
        else:
            return "Unknown command. Try /add, /list, or /done <id>."
    
    def poll_and_handle(self) -> None:
        """Poll Telegram for updates and handle commands."""
        updates = self.get_updates()
        chat_id = str(self.config.get('chat_id', ''))
        
        for update in updates:
            msg = update.get('message', {})
            text = msg.get('text', '')
            from_chat_id = str(msg.get('chat', {}).get('id', ''))
            
            if text and from_chat_id == chat_id and text.startswith('/'):
                response = self.handle_command(from_chat_id, text)
                self.send_message(from_chat_id, response)


def demo_mode() -> None:
    """Run in demo mode: load demo.json and execute with fake clock."""
    demo_path = os.path.join(os.path.dirname(__file__), 'demo.json')
    
    if not os.path.exists(demo_path):
        print("Error: demo.json not found.")
        sys.exit(1)
    
    with open(demo_path, 'r') as f:
        demo = json.load(f)
    
    # Extract demo data
    config_data = demo.get('config', {})
    initial_state = demo.get('state', {})
    
    # Set up fake clock
    fake_time = demo.get('fake_time', '2024-01-01T12:00:00Z')
    def fake_now():
        return fake_time
    
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
        
        # Create bot and run
        bot = TaskReminder(config, store, notifier, fake_clock=fake_now)
        
        # Run check_due_tasks to send any due reminders
        bot.check_due_tasks()
        
        print("Demo completed.")
    finally:
        # Clean up temp file
        try:
            os.unlink(temp_store_path)
        except OSError:
            pass


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Telegram task-reminder bot.')
    parser.add_argument('--demo', action='store_true', help='Run in demo mode (offline, no tokens needed)')
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
    
    # Create bot
    bot = TaskReminder(config, store, notifier)
    
    # Define scheduler jobs
    jobs = {
        'check_reminders': bot.check_due_tasks,
        'poll_telegram': bot.poll_and_handle
    }
    
    # Run loop
    print("Bot started. Press Ctrl+C to stop.")
    try:
        while True:
            result = run_loop(jobs, store, notifier, ticks=1)
            time.sleep(5)  # Poll every 5 seconds
    except KeyboardInterrupt:
        print("\nBot stopped.")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
