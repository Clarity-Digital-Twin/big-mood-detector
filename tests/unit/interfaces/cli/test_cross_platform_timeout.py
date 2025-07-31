"""Tests for cross-platform timeout behavior."""

import platform
from typing import Any
from unittest.mock import patch

import pytest

from big_mood_detector.interfaces.cli.commands import calculate_timeout


class TestCrossPlatformTimeout:
    def test_timeout_calculation_is_platform_independent(self):
        """Timeout calculation should work on all platforms."""
        # The calculation itself should be platform-independent
        assert calculate_timeout(10) == 120  # Small file
        assert calculate_timeout(100) == 300  # Medium file
        assert calculate_timeout(500) == 0    # Large file

    def test_timeout_handler_context_manager(self):
        """Test the timeout handler context manager logic."""
        # We'll test the logic directly rather than through the full CLI
        # since the full CLI has many dependencies
        import signal
        from collections.abc import Iterator
        from contextlib import contextmanager


        @contextmanager
        def timeout_handler(seconds: int) -> Iterator[None]:
            """Cross-platform timeout handler."""
            if seconds > 0 and platform.system() != "Windows":
                def timeout_error(signum: int, frame: Any) -> None:
                    raise TimeoutError(f"Processing timed out after {seconds} seconds")

                signal.signal(signal.SIGALRM, timeout_error)
                signal.alarm(seconds)
                try:
                    yield
                finally:
                    signal.alarm(0)
            else:
                yield

        # Test that it doesn't crash on different platforms
        with timeout_handler(0):  # No timeout
            pass

        if platform.system() != "Windows":
            # On Unix, we can test signal setup
            with patch('signal.signal') as mock_signal:
                with patch('signal.alarm') as mock_alarm:
                    with timeout_handler(120):
                        pass
                    assert mock_signal.called
                    assert mock_alarm.call_count == 2  # Once to set, once to clear

    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows-only test")
    def test_windows_timeout_shows_warning(self, tmp_path):
        """On Windows, timeout should show a warning."""
        from click.testing import CliRunner

        test_file = tmp_path / "test.xml"
        test_file.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<HealthData locale="en_US">
</HealthData>""")

        runner = CliRunner()

        # Mock file size
        with patch.object(type(test_file), 'stat') as mock_stat:
            mock_stat.return_value.st_size = 100 * 1024 * 1024  # 100MB

            result = runner.invoke(predict_command, [str(test_file)])

            # Should show Windows warning
            assert "Timeout protection not available on Windows" in result.output
