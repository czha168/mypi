import subprocess
from pathlib import Path
from unittest import mock

import pytest

# Import after configuring path? The test file is under tests/unit. Python will locate codepi package.
from codepi.addons import attribution


@pytest.fixture
def tmp_dir(tmp_path):
    """Provide a temporary working directory context."""
    cwd = tmp_path
    yield cwd
    # cleanup automatically by pytest


@mock.patch("subprocess.run")
def test_attribution_creates_file_and_configures_git(mock_run, tmp_dir, monkeypatch):
    # Ensure we are in the temporary directory
    monkeypatch.chdir(tmp_dir)

    # Simulate git config success
    mock_run.return_value = mock.Mock(returncode=0)

    # Run on_startup
    attribution.on_startup()

    # Verify file created
    ack = tmp_dir / ".codepi.acknowledgement"
    assert ack.exists()
    assert ack.read_text(encoding="utf-8") == "\nCo-authored-by: CodePi <codepi@users.noreply.github.com>\n"

    # Verify git config was called once with the right arguments
    mock_run.assert_called_once_with(
        ["git", "config", "--local", "commit.template", ".codepi.acknowledgement"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


@mock.patch("subprocess.run")
def test_attribution_idempotent(mock_run, tmp_dir, monkeypatch):
    # Already exists file
    ack = tmp_dir / ".codepi.acknowledgement"
    ack.write_text("\nAlready there\n", encoding="utf-8")
    monkeypatch.chdir(tmp_dir)

    mock_run.return_value = mock.Mock(returncode=0)
    attribution.on_startup()

    # Should not overwrite content
    assert ack.read_text(encoding="utf-8") == "\nAlready there\n"
    mock_run.assert_called_once_with(
        ["git", "config", "--local", "commit.template", ".codepi.acknowledgement"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )