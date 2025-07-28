"""Test Docker path configuration and volume mounting."""

import subprocess

import pytest


@pytest.mark.integration
class TestDockerPaths:
    """Test that Docker container handles paths correctly."""

    @pytest.fixture
    def docker_image(self):
        """Ensure Docker image is available."""
        # Check if image exists
        result = subprocess.run(
            ["docker", "images", "-q", "big-mood-detector:latest"],
            capture_output=True,
            text=True,
        )
        if not result.stdout.strip():
            pytest.skip("Docker image not built")
        return "big-mood-detector:latest"

    def test_data_dir_environment_variable(self, docker_image):
        """Test that BIGMOOD_DATA_DIR is properly set in container."""
        result = subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                docker_image,
                "bash",
                "-c",
                "echo $BIGMOOD_DATA_DIR",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == "/app/data"

    def test_settings_use_correct_paths(self, docker_image):
        """Test that Python settings use the correct data directory."""
        result = subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                docker_image,
                "python",
                "-c",
                "from big_mood_detector.infrastructure.settings import get_settings; "
                "s = get_settings(); "
                "print(f'DATA_DIR: {s.DATA_DIR}'); "
                "print(f'OUTPUT_DIR: {s.OUTPUT_DIR}')",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        lines = result.stdout.strip().split("\n")
        assert "DATA_DIR: /app/data" in lines[0]
        assert "OUTPUT_DIR: /app/data/output" in lines[1]

    def test_cli_process_no_permission_warnings(self, docker_image, tmp_path):
        """Test that CLI process command doesn't show permission warnings."""
        # Create a minimal test file
        test_file = tmp_path / "test.json"
        test_file.write_text('{"test": "data"}')

        result = subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "-v",
                f"{tmp_path}:/app/data/input",
                docker_image,
                "process",
                "--help",
            ],
            capture_output=True,
            text=True,
        )

        # Should not contain permission warnings
        assert "No write permission" not in result.stderr
        assert result.returncode == 0

    def test_entrypoint_creates_directories(self, docker_image, tmp_path):
        """Test that entrypoint creates required directories."""
        result = subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "-v",
                f"{tmp_path}:/app/data",
                docker_image,
                "bash",
                "-c",
                "ls -la /app/data/",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        # After entrypoint runs, these should exist
        expected_dirs = ["output", "uploads", "temp"]
        for dir_name in expected_dirs:
            # Check if directory was created
            check_result = subprocess.run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "-v",
                    f"{tmp_path}:/app/data",
                    docker_image,
                    "bash",
                    "-c",
                    f"test -d /app/data/{dir_name} && echo 'exists' || echo 'missing'",
                ],
                capture_output=True,
                text=True,
            )
            assert check_result.stdout.strip() == "exists", f"Directory {dir_name} not created"

    def test_volume_mount_permissions(self, docker_image, tmp_path):
        """Test that mounted volumes have correct permissions."""
        # Create test structure
        (tmp_path / "input").mkdir()
        (tmp_path / "input" / "test.xml").write_text("<test/>")

        result = subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "-v",
                f"{tmp_path}:/app/data",
                docker_image,
                "bash",
                "-c",
                "python -c 'from pathlib import Path; "
                "p = Path(\"/app/data/output/test.txt\"); "
                "p.parent.mkdir(exist_ok=True); "
                "p.write_text(\"test\"); "
                "print(\"SUCCESS\")'",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "SUCCESS" in result.stdout
        assert (tmp_path / "output" / "test.txt").exists()
