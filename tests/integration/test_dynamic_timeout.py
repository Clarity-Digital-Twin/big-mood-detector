"""Integration test for dynamic timeout functionality."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from big_mood_detector.interfaces.cli.commands import predict_command


class TestDynamicTimeout:
    def test_small_file_uses_standard_timeout(self, tmp_path):
        """Small files should use 2-minute timeout."""
        # Create a small test file (10MB)
        test_file = tmp_path / "small_export.xml"
        test_file.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE HealthData>
<HealthData locale="en_US">
  <ExportDate value="2025-01-31 09:08:45 -0800"/>
</HealthData>""")
        
        runner = CliRunner()
        
        # Mock the file size
        with patch.object(Path, 'stat') as mock_stat:
            mock_stat.return_value.st_size = 10 * 1024 * 1024  # 10MB
            
            result = runner.invoke(predict_command, [str(test_file)])
            
            # Should not show large file warning
            assert "Large file detected" not in result.output
    
    def test_medium_file_shows_timeout_message(self, tmp_path):
        """Medium files should show timeout message."""
        test_file = tmp_path / "medium_export.xml"
        test_file.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE HealthData>
<HealthData locale="en_US">
  <ExportDate value="2025-01-31 09:08:45 -0800"/>
</HealthData>""")
        
        runner = CliRunner()
        
        # Mock the file size (100MB)
        with patch.object(Path, 'stat') as mock_stat:
            mock_stat.return_value.st_size = 100 * 1024 * 1024  # 100MB
            
            result = runner.invoke(predict_command, [str(test_file)])
            
            # Should show processing message with timeout
            assert "Processing 100MB file (timeout: 5 minutes)" in result.output
    
    def test_large_file_shows_no_timeout_warning(self, tmp_path):
        """Large files should show no timeout warning."""
        test_file = tmp_path / "large_export.xml"
        test_file.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE HealthData>
<HealthData locale="en_US">
  <ExportDate value="2025-01-31 09:08:45 -0800"/>
</HealthData>""")
        
        runner = CliRunner()
        
        # Mock the file size (500MB)
        with patch.object(Path, 'stat') as mock_stat:
            mock_stat.return_value.st_size = 500 * 1024 * 1024  # 500MB
            
            result = runner.invoke(predict_command, [str(test_file)])
            
            # Should show large file message
            assert "Large file detected (500MB)" in result.output
            assert "Processing may take 10-15 minutes" in result.output