"""
logger.py: Logging setup for Macktechs DriveKit
"""

import logging
import os
from pathlib import Path


def setup_logging() -> logging.Logger:
    log_dir = Path.home() / "Library" / "Logs" / "MacktechsDriveKit"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "drivekit.log"

    logger = logging.getLogger("drivekit")
    logger.setLevel(logging.DEBUG)

    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    ))

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(
        "[%(levelname)s] %(message)s"
    ))

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
