"""Automated attribution addon.

This module implements a lightweight hook that runs when CodePi starts. It checks for
-a ``.codepi.acknowledgement`` file in the current working directory. If the file
-does not exist, it creates it with a blank line followed by the standard
-Co‑authored‑by: line used by Git commit‑message templates. Finally it executes
-``git config --local commit.template .codepi.acknowledgement`` so that any
-commit made while the repository is open will automatically include the
-attribution line.
-"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import List

#: The default content to write when the file is created.
_DEFAULT_CONTENT = "\nCo-authored-by: CodePi <codepi@users.noreply.github.com>\n"


def _execute_git_config(template_path: Path) -> None:
    """Run the ``git config`` command.

    Parameters
    ----------
    template_path: Path
        The path to the template file relative to the repository root.
    """
    try:
        subprocess.run(
            ["git", "config", "--local", "commit.template", template_path.name],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except subprocess.CalledProcessError as exc:  # pragma: no cover - defensive
        raise RuntimeError(f"Failed to set Git template: {exc.stderr.decode().strip()}")


def on_startup() -> None:
    """Entry point executed from :mod:`codepi.__main__`.

    The function performs three steps:

    1. Detect whether ``.codepi.acknowledgement`` exists in the current
       working directory.
    2. If missing, create the file with the required content.
    3. Configure Git to use the file as the commit message template.
    """
    cwd = Path.cwd()
    template = cwd / ".codepi.acknowledgement"

    # 1. Create if needed
    if not template.exists():
        template.write_text(_DEFAULT_CONTENT, encoding="utf-8")

    # 2 & 3. Configure Git – use relative path to keep the config portable.
    _execute_git_config(template)
