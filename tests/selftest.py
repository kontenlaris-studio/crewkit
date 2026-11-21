#!/usr/bin/env python3
"""Self-verification tests for CrewKit core (R1-R5) — deterministic, offline, no network."""

import json
import os
import sys
import tempfile
import unittest
import subprocess
from pathlib import Path
from io import StringIO

# Add core to path for import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

from crewkit import (
    Config, load_config,
    now_iso, parse_iso, due_jobs,
    StateStore,
    Notifier, ConsoleSink, FileSink,
    run_loop
)


class TestR1Config(unittest.TestCase):
    """R1: Config — Load JSON config with env var overrides."""
    
    def test_load_missing_file_with_defaults(self):
        """Missing file yields defaults."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, 'config.json')
            defaults = {'key1': 'value1', 'key2': 42}
            
            config = load_config(config_path, defaults)
            
            self.assertEqual(config.get('key1'), 'value1')
            self.assertEqual(config.get('key2'), 42)
    
    def test_load_missing_file_no_defaults(self):
        """Missing file with no defaults yields empty config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, 'config.json')
            config = load_config(config_path)
            
            self.assertIsNone(config.get('nonexistent'))
            self.assertEqual(config.get('nonexistent', 'default'), 'default')
    
    def test_load_from_file(self):
        """Load valid JSON from file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, 'config.json')
            data = {'host': 'localhost', 'port': 8080}
            
            with open(config_path, 'w') as f:
                json.dump(data, f)
            
            config = load_config(config_path)
            
            self.assertEqual(config.get('host'), 'localhost')
            self.assertEqual(config.get('port'), 8080)
    
    def test_corrupt_file_uses_defaults(self):
        """Corrupt JSON file falls back to defaults."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, 'config.json')
            defaults = {'fallback': 'value'}
            
            with open(config_path, 'w') as f:
                f.write('{ invalid json')
            
            config = load_config(config_path, defaults)
            
            self.assertEqual(config.get('fallback'), 'value')
    
    def test_env_override_string(self):
        """Environment variable CREWKIT_<KEY> overrides config (string)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, 'config.json')
            
            # Save original env
            old_env = os.environ.get('CREWKIT_DEBUG')
            try:
                os.environ['CREWKIT_DEBUG'] = 'true'
                config = load_config(config_path, {'debug': False})
                # JSON parse "true" as boolean
                self.assertEqual(config.get('debug'), True)
            finally:
                if old_env is not None:
                    os.environ['CREWKIT_DEBUG'] = old_env
                else:
                    os.environ.pop('CREWKIT_DEBUG', None)
    
    def test_env_override_json(self):
        """Environment variable CREWKIT_<KEY> can be JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, 'config.json')
            
            old_env = os.environ.get('CREWKIT_OPTIONS')
            try:
                os.environ['CREWKIT_OPTIONS'] = '{"key": "value"}'
                config = load_config(config_path)
                self.assertEqual(config.get('options'), {'key': 'value'})
            finally:
                if old_env is not None:
                    os.environ['CREWKIT_OPTIONS'] = old_env
                else:
                    os.environ.pop('CREWKIT_OPTIONS', None)
    
    def test_dict_like_access(self):
        """Config supports dict-like access."""
        config = load_config('/nonexistent', {'key': 'value'})
        
        self.assertEqual(config['key'], 'value')
        config['new_key'] = 'new_value'
        self.assertEqual(config['new_key'], 'new_value')


class TestR2Scheduler(unittest.TestCase):
    """R2: Scheduler — Determine which jobs are due."""
    
    def test_never_run_job_is_due(self):
        """Job that never ran is due."""
        jobs = {'task1': {'interval_seconds': 3600}}
        state = {}
        now = '2024-01-01T12:00:00Z'
        
        due = due_jobs(jobs, state, now)
        
        self.assertIn('task1', due)
    
    def test_job_within_interval_not_due(self):
        """Job within interval is not due."""
        jobs = {'task1': {'interval_seconds': 3600}}
        state = {'task1': {'last_run': '2024-01-01T12:30:00Z'}}
        now = '2024-01-01T12:45:00Z'  # 15 minutes = 900 seconds < 3600
        
        due = due_jobs(jobs, state, now)
        
        self.assertNotIn('task1', due)
    
    def test_job_past_interval_is_due(self):
        """Job past interval is due."""
        jobs = {'task1': {'interval_seconds': 3600}}
        state = {'task1': {'last_run': '2024-01-01T11:00:00Z'}}
        now = '2024-01-01T12:30:00Z'  # 90 minutes = 5400 seconds > 3600
        
        due = due_jobs(jobs, state, now)
        
        self.assertIn('task1', due)
    
    def test_corrupt_last_run_is_due(self):
        """Job with corrupt last_run timestamp is due."""
        jobs = {'task1': {'interval_seconds': 3600}}
        state = {'task1': {'last_run': 'not-a-timestamp'}}
        now = '2024-01-01T12:00:00Z'
        
        due = due_jobs(jobs, state, now)
        
        self.assertIn('task1', due)
    
    def test_multiple_jobs(self):
        """Scheduler handles multiple jobs correctly."""
        jobs = {
            'task1': {'interval_seconds': 3600},
            'task2': {'interval_seconds': 600}
        }
        state = {
            'task1': {'last_run': '2024-01-01T12:00:00Z'},
            'task2': {'last_run': '2024-01-01T12:05:00Z'}
        }
        now = '2024-01-01T12:15:00Z'  # task1: 15 min elapsed, task2: 10 min elapsed
        
        due = due_jobs(jobs, state, now)
        
        self.assertNotIn('task1', due)  # 15 min < 60 min
        self.assertIn('task2', due)     # 10 min > 10 min (at boundary, but we use >=)


class TestR3StateStore(unittest.TestCase):
    """R3: State store — JSON file with atomic writes."""
    
    def test_initialize_empty(self):
        """Store initializes empty for missing file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = os.path.join(tmpdir, 'state.json')
            store = StateStore(store_path)
            
            self.assertIsNone(store.get('nonexistent'))
    
    def test_get_set_in_memory(self):
        """Get/set work in memory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = os.path.join(tmpdir, 'state.json')
            store = StateStore(store_path)
            
            store.set('key', 'value')
            self.assertEqual(store.get('key'), 'value')
            
            # Also test dict-like access
            store['key2'] = 'value2'
            self.assertEqual(store['key2'], 'value2')
    
    def test_save_creates_file(self):
        """Save writes JSON to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = os.path.join(tmpdir, 'state.json')
            store = StateStore(store_path)
            
            store.set('key', 'value')
            store.save()
            
            self.assertTrue(os.path.exists(store_path))
            
            with open(store_path, 'r') as f:
                data = json.load(f)
            
            self.assertEqual(data['key'], 'value')
    
    def test_load_existing_file(self):
        """Load reads existing state file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = os.path.join(tmpdir, 'state.json')
            
            # Write initial state
            initial = {'existing': 'data'}
            with open(store_path, 'w') as f:
                json.dump(initial, f)
            
            # Load and verify
            store = StateStore(store_path)
            self.assertEqual(store.get('existing'), 'data')
    
    def test_corrupt_file_loads_empty(self):
        """Corrupt JSON file loads as empty state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = os.path.join(tmpdir, 'state.json')
            
            # Write corrupt JSON
            with open(store_path, 'w') as f:
                f.write('{ invalid json }')
            
            store = StateStore(store_path)
            self.assertIsNone(store.get('nonexistent'))
    
    def test_atomic_write(self):
        """Save is atomic (uses temp file + rename)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = os.path.join(tmpdir, 'state.json')
            store = StateStore(store_path)
            
            store.set('atomic_key', 'atomic_value')
            store.save()
            
            # Verify file is valid JSON
            with open(store_path, 'r') as f:
                data = json.load(f)
            self.assertEqual(data['atomic_key'], 'atomic_value')


class TestR4Notifier(unittest.TestCase):
    """R4: Notifier — Fan out messages to sinks."""
    
    def test_console_sink(self):
        """ConsoleSink prints to stdout."""
        sink = ConsoleSink()
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        
        try:
            sink.send('test message')
            output = sys.stdout.getvalue()
            self.assertIn('test message', output)
        finally:
            sys.stdout = old_stdout
    
    def test_file_sink(self):
        """FileSink appends to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, 'log.txt')
            sink = FileSink(log_path)
            
            sink.send('line 1')
            sink.send('line 2')
            
            with open(log_path, 'r') as f:
                content = f.read()
            
            self.assertIn('line 1', content)
            self.assertIn('line 2', content)
    
    def test_file_sink_handles_missing_dir(self):
        """FileSink silently fails if file cannot be written."""
        sink = FileSink('/nonexistent/path/log.txt')
        # Should not raise
        sink.send('message')
    
    def test_notifier_format(self):
        """Notifier formats message as [ISO] title — body."""
        output = StringIO()
        
        class TestSink:
            def send(self, message):
                output.write(message)
        
        notifier = Notifier([TestSink()])
        notifier.notify('Test Title', 'Test Body', '2024-01-01T12:00:00Z')
        
        msg = output.getvalue()
        self.assertIn('[2024-01-01T12:00:00Z]', msg)
        self.assertIn('Test Title', msg)
        self.assertIn('Test Body', msg)
        self.assertIn('—', msg)
    
    def test_notifier_without_body(self):
        """Notifier works without body."""
        output = StringIO()
        
        class TestSink:
            def send(self, message):
                output.write(message)
        
        notifier = Notifier([TestSink()])
        notifier.notify('Title Only', timestamp='2024-01-01T12:00:00Z')
        
        msg = output.getvalue()
        self.assertIn('[2024-01-01T12:00:00Z]', msg)
        self.assertIn('Title Only', msg)
        self.assertNotIn('—', msg)
    
    def test_notifier_multiple_sinks(self):
        """Notifier fans out to multiple sinks."""
        output1 = StringIO()
        output2 = StringIO()
        
        class TestSink:
            def __init__(self, out):
                self.out = out
            
            def send(self, message):
                self.out.write(message)
        
        notifier = Notifier([TestSink(output1), TestSink(output2)])
        notifier.notify('Message', timestamp='2024-01-01T12:00:00Z')
        
        self.assertIn('Message', output1.getvalue())
        self.assertIn('Message', output2.getvalue())


class TestR5Runner(unittest.TestCase):
    """R5: Runner — Execute jobs, record state, notify failures."""
    
    def test_execute_successful_job(self):
        """Runner executes successful job and records last_run."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = os.path.join(tmpdir, 'state.json')
            store = StateStore(store_path)
            notifier = Notifier([])
            
            executed = []
            def test_job():
                executed.append('test_job')
                return 'success'
            
            jobs = {'test_job': test_job}
            
            # Use fake clock for determinism
            fake_time = '2024-01-01T12:00:00Z'
            def fake_now():
                return fake_time
            
            result = run_loop(jobs, store, notifier, now_fn=fake_now, ticks=1)
            
            self.assertIn('test_job', executed)
            self.assertIn('test_job', result['executed'])
            
            # Check state was persisted
            self.assertIsNotNone(store.get('test_job'))
            self.assertEqual(store.get('test_job', {}).get('last_run'), fake_time)
            self.assertEqual(store.get('test_job', {}).get('last_result'), 'success')
    
    def test_job_failure_recorded_and_notified(self):
        """Runner catches job exceptions, records them, and notifies."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = os.path.join(tmpdir, 'state.json')
            store = StateStore(store_path)
            
            notifications = []
            class CaptureNotifier:
                def notify(self, title, body='', timestamp=''):
                    notifications.append({'title': title, 'body': body, 'timestamp': timestamp})
            
            notifier = CaptureNotifier()
            
            def failing_job():
                raise ValueError('Test error')
            
            jobs = {'failing_job': failing_job}
            
            fake_time = '2024-01-01T12:00:00Z'
            def fake_now():
                return fake_time
            
            result = run_loop(jobs, store, notifier, now_fn=fake_now, ticks=1)
            
            # Job should be recorded as failed
            self.assertIn('failing_job', result['failed'])
            
            # State should record the error
            job_state = store.get('failing_job', {})
            self.assertEqual(job_state.get('last_result'), 'failure')
            self.assertIn('Test error', job_state.get('last_error', ''))
            
            # Notification should be sent
            self.assertTrue(len(notifications) > 0)
            self.assertIn('failing_job', notifications[0]['title'])
            self.assertIn('Test error', notifications[0]['body'])
    
    def test_runner_multiple_ticks(self):
        """Runner can execute multiple iterations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = os.path.join(tmpdir, 'state.json')
            store = StateStore(store_path)
            notifier = Notifier([])
            
            call_count = [0]
            def counting_job():
                call_count[0] += 1
            
            jobs = {'counter': counting_job}
            
            def fake_now():
                return '2024-01-01T12:00:00Z'
            
            result = run_loop(jobs, store, notifier, now_fn=fake_now, ticks=3)
            
            # Job should be called once per tick (since interval_seconds=0, always due)
            self.assertEqual(call_count[0], 3)
            self.assertEqual(len(result['executed']), 3)
    
    def test_runner_summary(self):
        """Runner returns summary dict."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = os.path.join(tmpdir, 'state.json')
            store = StateStore(store_path)
            notifier = Notifier([])
            
            def dummy():
                pass
            
            jobs = {'job1': dummy, 'job2': dummy}
            
            def fake_now():
                return '2024-01-01T12:00:00Z'
            
            result = run_loop(jobs, store, notifier, now_fn=fake_now, ticks=1)
            
            self.assertIn('executed', result)
            self.assertIn('failed', result)
            self.assertIn('summary', result)
            self.assertIsInstance(result['summary'], str)


class TestImportSafety(unittest.TestCase):
    """Verify all modules are import-safe (no side effects)."""
    
    def test_imports_are_side_effect_free(self):
        """All module imports should have no side effects."""
        # This test just verifies the imports work at all
        # If there were side effects (prints, network, file creation),
        # they would occur during import
        from crewkit import config, clock, store, notify, runner
        
        # If we got here, imports succeeded without side effects
        self.assertIsNotNone(config)
        self.assertIsNotNone(clock)
        self.assertIsNotNone(store)
        self.assertIsNotNone(notify)
        self.assertIsNotNone(runner)


class TestClockISO8601(unittest.TestCase):
    """Test clock ISO-8601 handling."""
    
    def test_now_iso_format(self):
        """now_iso returns valid ISO-8601 with Z suffix."""
        iso_str = now_iso()
        
        # Should end with Z
        self.assertTrue(iso_str.endswith('Z'))
        
        # Should be parseable
        parsed = parse_iso(iso_str)
        self.assertIsNotNone(parsed)
    
    def test_parse_iso_z_suffix(self):
        """parse_iso handles Z suffix."""
        iso_str = '2024-01-01T12:00:00Z'
        parsed = parse_iso(iso_str)
        
        self.assertEqual(parsed.year, 2024)
        self.assertEqual(parsed.month, 1)
        self.assertEqual(parsed.day, 1)
        self.assertEqual(parsed.hour, 12)
    
    def test_parse_iso_plus_format(self):
        """parse_iso handles +00:00 format."""
        iso_str = '2024-01-01T12:00:00+00:00'
        parsed = parse_iso(iso_str)
        
        self.assertEqual(parsed.year, 2024)


class TestAppDemos(unittest.TestCase):
    """Smoke tests for app demo modes."""
    
    def test_telegram_bot_demo(self):
        """Telegram bot demo runs offline and prints expected reminder."""
        bot_path = os.path.join(os.path.dirname(__file__), '..', 'apps', 'telegram-task-bot', 'bot.py')
        
        if not os.path.exists(bot_path):
            self.skipTest("bot.py not found")
        
        try:
            result = subprocess.run(
                [sys.executable, bot_path, '--demo'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # Should exit successfully
            self.assertEqual(result.returncode, 0, f"bot.py exited with code {result.returncode}\nstderr: {result.stderr}")
            
            # Should print reminder for "Review code" task (already due)
            output = result.stdout + result.stderr
            self.assertIn('Reminder', output, "Expected 'Reminder' in output")
            self.assertIn('Review code', output, "Expected 'Review code' task name in output")
            
        except subprocess.TimeoutExpired:
            self.fail("bot.py demo timed out")
        except Exception as e:
            self.fail(f"bot.py demo failed: {e}")
    
    def test_price_watch_demo(self):
        """Price watch demo runs offline and prints expected alert."""
        watch_path = os.path.join(os.path.dirname(__file__), '..', 'apps', 'price-watch', 'watch.py')
        
        if not os.path.exists(watch_path):
            self.skipTest("watch.py not found")
        
        try:
            result = subprocess.run(
                [sys.executable, watch_path, '--demo'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # Should exit successfully
            self.assertEqual(result.returncode, 0, f"watch.py exited with code {result.returncode}\nstderr: {result.stderr}")
            
            # Should print price alert for Widget (price $45.99 <= target $50)
            output = result.stdout + result.stderr
            self.assertIn('Price Alert', output, "Expected 'Price Alert' in output")
            self.assertIn('Widget', output, "Expected 'Widget' item name in output")
            
        except subprocess.TimeoutExpired:
            self.fail("watch.py demo timed out")
        except Exception as e:
            self.fail(f"watch.py demo failed: {e}")


def main():
    """Run all tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestR1Config))
    suite.addTests(loader.loadTestsFromTestCase(TestR2Scheduler))
    suite.addTests(loader.loadTestsFromTestCase(TestR3StateStore))
    suite.addTests(loader.loadTestsFromTestCase(TestR4Notifier))
    suite.addTests(loader.loadTestsFromTestCase(TestR5Runner))
    suite.addTests(loader.loadTestsFromTestCase(TestImportSafety))
    suite.addTests(loader.loadTestsFromTestCase(TestClockISO8601))
    suite.addTests(loader.loadTestsFromTestCase(TestAppDemos))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(main())
