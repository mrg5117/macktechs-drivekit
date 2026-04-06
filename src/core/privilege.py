"""
privilege.py: Privilege escalation for disk operations
"""

import logging
import subprocess
import tempfile
import os
from pathlib import Path
from typing import Optional, Callable

logger = logging.getLogger("drivekit.privilege")


def run_privileged(command: str, progress_log: Optional[str] = None) -> subprocess.Popen:
    """
    Run a command with root privileges via osascript.

    If progress_log is provided, the command's output is tee'd to that file
    so progress can be monitored by the caller.
    """
    if progress_log:
        # Wrap command to write output to a log file for progress monitoring
        wrapped = f'{command} 2>&1 | tee "{progress_log}"; echo "DRIVEKIT_DONE" >> "{progress_log}"'
        escaped = wrapped.replace("\\", "\\\\").replace('"', '\\"')
        script = f'do shell script "/bin/bash -c \\"{escaped}\\"" with administrator privileges'
    else:
        escaped = command.replace("\\", "\\\\").replace('"', '\\"')
        script = f'do shell script "{escaped}" with administrator privileges'

    logger.info(f"Running privileged: {command}")

    proc = subprocess.Popen(
        ["osascript", "-e", script],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return proc


def run_privileged_script(commands: list[str], progress_log: Optional[str] = None) -> subprocess.Popen:
    """
    Write multiple commands to a temp script and run it with root privileges.
    Useful for chaining operations like partition + flash.
    """
    script_file = tempfile.NamedTemporaryFile(
        mode="w", suffix=".sh", prefix="drivekit_", delete=False
    )
    script_file.write("#!/bin/bash\nset -e\n")
    if progress_log:
        script_file.write(f'exec > >(tee "{progress_log}") 2>&1\n')
    for cmd in commands:
        script_file.write(f"{cmd}\n")
    if progress_log:
        script_file.write(f'echo "DRIVEKIT_DONE" >> "{progress_log}"\n')
    script_file.close()
    os.chmod(script_file.name, 0o755)

    logger.info(f"Running privileged script with {len(commands)} commands")

    escaped = script_file.name.replace('"', '\\"')
    proc = subprocess.Popen(
        ["osascript", "-e",
         f'do shell script "{escaped}" with administrator privileges'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return proc


def run_simple(command: str) -> subprocess.CompletedProcess:
    """Run a non-privileged command and return the result."""
    logger.debug(f"Running: {command}")
    return subprocess.run(
        command, shell=True, capture_output=True, text=True, timeout=30
    )
