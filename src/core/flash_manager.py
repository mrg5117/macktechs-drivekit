"""
flash_manager.py: Flash macOS installers to partitions using createinstallmedia
"""

import logging
import os
import re
import tempfile
import time
import threading
from pathlib import Path
from typing import Optional, Callable

from .privilege import run_privileged, run_privileged_script

logger = logging.getLogger("drivekit.flash")


class FlashOperation:
    """Manages flashing a single installer to a target volume."""

    def __init__(self, installer_app: str, target_volume: str):
        self.installer_app = installer_app
        self.target_volume = target_volume
        self.progress: float = 0.0
        self.status: str = "pending"
        self.error: Optional[str] = None
        self._progress_log: Optional[str] = None
        self._proc = None
        self._monitor_thread = None

    @property
    def createinstallmedia_path(self) -> str:
        return f"{self.installer_app}/Contents/Resources/createinstallmedia"

    def start(self, on_progress: Optional[Callable] = None,
              on_complete: Optional[Callable] = None):
        """Start the flash operation in a background thread."""
        self._on_progress = on_progress
        self._on_complete = on_complete

        # Create progress log
        fd, self._progress_log = tempfile.mkstemp(
            prefix="drivekit_flash_", suffix=".log"
        )
        os.close(fd)

        cmd = (
            f'"{self.createinstallmedia_path}" '
            f'--volume "{self.target_volume}" --nointeraction'
        )

        self.status = "running"
        self._proc = run_privileged(cmd, progress_log=self._progress_log)

        # Start monitoring thread
        self._monitor_thread = threading.Thread(
            target=self._monitor_progress, daemon=True
        )
        self._monitor_thread.start()

    def _monitor_progress(self):
        """Monitor the progress log file for updates."""
        last_size = 0
        content = ""

        while True:
            try:
                if self._progress_log and os.path.exists(self._progress_log):
                    with open(self._progress_log, "r") as f:
                        content = f.read()

                    # Parse createinstallmedia progress
                    # Output format: "Erasing disk: 0%... 10%..." or "Copying to disk: 0%..."
                    percentages = re.findall(r"(\d+)%", content)
                    if percentages:
                        self.progress = float(percentages[-1])

                    # Determine phase
                    if "Erasing disk" in content:
                        self.status = "erasing"
                    elif "Copying" in content:
                        self.status = "copying"
                    elif "Making disk bootable" in content:
                        self.status = "finalizing"
                        self.progress = 95.0
                    elif "Install media now available" in content:
                        self.status = "complete"
                        self.progress = 100.0

                    if self._on_progress:
                        self._on_progress(self)

                    if "DRIVEKIT_DONE" in content:
                        break

            except Exception as e:
                logger.debug(f"Progress monitor: {e}")

            # Check if process has exited
            if self._proc and self._proc.poll() is not None:
                break

            time.sleep(0.5)

        # Final status
        if self._proc:
            self._proc.wait()
            if self._proc.returncode != 0 and self.status != "complete":
                self.status = "error"
                stderr = self._proc.stderr.read() if self._proc.stderr else ""
                self.error = stderr or "Flash operation failed"
                logger.error(f"Flash failed: {self.error}")
            elif self.status != "error":
                self.status = "complete"
                self.progress = 100.0

        if self._on_complete:
            self._on_complete(self)

        # Cleanup
        try:
            if self._progress_log and os.path.exists(self._progress_log):
                os.unlink(self._progress_log)
        except Exception:
            pass

    @property
    def display_status(self) -> str:
        name = Path(self.installer_app).stem.replace("Install ", "")
        statuses = {
            "pending": f"{name}: Waiting...",
            "running": f"{name}: Starting...",
            "erasing": f"{name}: Erasing disk ({self.progress:.0f}%)",
            "copying": f"{name}: Copying files ({self.progress:.0f}%)",
            "finalizing": f"{name}: Making bootable...",
            "complete": f"{name}: Complete",
            "error": f"{name}: Error - {self.error}",
        }
        return statuses.get(self.status, f"{name}: {self.status}")


class FlashQueue:
    """Queue multiple flash operations to run sequentially."""

    def __init__(self):
        self.operations: list[FlashOperation] = []
        self.current_index: int = -1
        self._on_progress: Optional[Callable] = None
        self._on_all_complete: Optional[Callable] = None
        self._running = False

    def add(self, installer_app: str, target_volume: str):
        op = FlashOperation(installer_app, target_volume)
        self.operations.append(op)

    def start(self, on_progress: Optional[Callable] = None,
              on_all_complete: Optional[Callable] = None):
        """Start processing the queue."""
        self._on_progress = on_progress
        self._on_all_complete = on_all_complete
        self._running = True
        self._run_next()

    def _run_next(self):
        self.current_index += 1
        if self.current_index >= len(self.operations):
            self._running = False
            if self._on_all_complete:
                self._on_all_complete()
            return

        op = self.operations[self.current_index]
        op.start(
            on_progress=self._on_progress,
            on_complete=lambda op: self._run_next(),
        )

    @property
    def overall_progress(self) -> float:
        if not self.operations:
            return 0.0
        completed = sum(1 for op in self.operations if op.status == "complete")
        current_progress = 0
        if 0 <= self.current_index < len(self.operations):
            current_progress = self.operations[self.current_index].progress / 100
        return ((completed + current_progress) / len(self.operations)) * 100

    @property
    def status_summary(self) -> str:
        total = len(self.operations)
        completed = sum(1 for op in self.operations if op.status == "complete")
        errors = sum(1 for op in self.operations if op.status == "error")
        if errors:
            return f"{completed}/{total} complete, {errors} errors"
        return f"{completed}/{total} complete"
