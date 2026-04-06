"""
installer_manager.py: Manage macOS installer downloads and discovery
"""

import logging
import re
import subprocess
from pathlib import Path
from typing import Optional

from ..models.installer import InstallerInfo
from ..utils.constants import INSTALLERS_DIR

logger = logging.getLogger("drivekit.installer")


def list_available_installers() -> list[InstallerInfo]:
    """
    Query Apple for available full macOS installers.
    Parses output of: softwareupdate --list-full-installers
    """
    logger.info("Fetching available installers from Apple...")
    try:
        result = subprocess.run(
            ["softwareupdate", "--list-full-installers"],
            capture_output=True, text=True, timeout=60
        )
    except subprocess.TimeoutExpired:
        logger.error("Timed out fetching installer list")
        return []

    installers = []
    pattern = re.compile(
        r"\* Title: (.+?), Version: (.+?), Size: (\d+)KiB, Build: (.+?), Deferred: (YES|NO)"
    )

    for line in result.stdout.splitlines():
        match = pattern.search(line)
        if match:
            title, version, size_kb, build, deferred = match.groups()
            inst = InstallerInfo(
                title=title.strip(),
                version=version.strip(),
                build=build.strip(),
                size_kb=int(size_kb),
                deferred=deferred == "YES",
            )
            installers.append(inst)

    # Check which ones are already downloaded
    downloaded = list_downloaded_installers()
    downloaded_builds = {d.build for d in downloaded}
    for inst in installers:
        if inst.build in downloaded_builds:
            inst.downloaded = True
            match = next((d for d in downloaded if d.build == inst.build), None)
            if match:
                inst.app_path = match.app_path

    logger.info(f"Found {len(installers)} available installers")
    return installers


def list_downloaded_installers() -> list[InstallerInfo]:
    """Scan /Applications for already-downloaded macOS installer apps."""
    installers = []
    apps_dir = Path(INSTALLERS_DIR)

    for app in sorted(apps_dir.glob("Install macOS*.app")):
        create_media = app / "Contents" / "Resources" / "createinstallmedia"
        if not create_media.exists():
            continue

        # Read version from Info.plist
        info_plist = app / "Contents" / "Info.plist"
        if not info_plist.exists():
            continue

        try:
            result = subprocess.run(
                ["defaults", "read", str(info_plist), "DTSDKBuild"],
                capture_output=True, text=True, timeout=5
            )
            build = result.stdout.strip()

            result2 = subprocess.run(
                ["defaults", "read", str(info_plist), "DTPlatformVersion"],
                capture_output=True, text=True, timeout=5
            )
            version = result2.stdout.strip()
        except subprocess.TimeoutExpired:
            continue

        if not build or not version:
            continue

        title = app.stem.replace("Install ", "")
        inst = InstallerInfo(
            title=title,
            version=version,
            build=build,
            size_kb=0,
            downloaded=True,
            app_path=str(app),
        )
        installers.append(inst)

    logger.info(f"Found {len(installers)} downloaded installers")
    return installers


def get_latest_per_major(installers: list[InstallerInfo]) -> list[InstallerInfo]:
    """
    Given a list of installers, return only the latest version
    for each major macOS release.
    """
    best: dict[str, InstallerInfo] = {}
    for inst in installers:
        major = inst.major_version
        if major not in best:
            best[major] = inst
        else:
            # Compare version strings
            from packaging.version import Version
            try:
                if Version(inst.version) > Version(best[major].version):
                    best[major] = inst
            except Exception:
                pass
    return sorted(best.values(), key=lambda i: i.version)


def download_installer(version: str, callback: Optional[callable] = None) -> subprocess.Popen:
    """
    Start downloading a macOS installer. Returns the Popen object.
    The caller should monitor for completion.
    """
    logger.info(f"Starting download of macOS {version}")
    proc = subprocess.Popen(
        ["softwareupdate", "--fetch-full-installer",
         "--full-installer-version", version],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return proc
