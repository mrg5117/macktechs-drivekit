#!/usr/bin/env python3
"""
Macktechs DriveKit — Multi-boot macOS installer drive builder
"""

import sys
from pathlib import Path

# Ensure parent of src is on the path so 'src' is a package
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.logger import setup_logging
from src.ui.main_window import MainWindow

import wx


def main():
    logger = setup_logging()
    logger.info("Starting Macktechs DriveKit")

    app = wx.App()
    frame = MainWindow()
    frame.Show()
    app.MainLoop()


if __name__ == "__main__":
    main()
