"""
disk_manager.py: External drive discovery and partitioning
"""

import logging
import re
import subprocess
from typing import Optional

from ..models.drive import DriveInfo, PartitionInfo, PartitionSpec
from .privilege import run_privileged, run_privileged_script

logger = logging.getLogger("drivekit.disk")


def list_external_drives() -> list[DriveInfo]:
    """List all external physical drives. Never returns internal drives."""
    result = subprocess.run(
        ["diskutil", "list", "-plist", "external", "physical"],
        capture_output=True, text=True, timeout=10
    )
    if result.returncode != 0:
        logger.warning("No external drives found")
        return []

    # Parse with plistlib for reliability
    import plistlib
    try:
        plist = plistlib.loads(result.stdout.encode())
    except Exception as e:
        logger.error(f"Failed to parse diskutil plist: {e}")
        return []

    drives = []
    for disk_id in plist.get("WholeDisks", []):
        info = get_drive_info(disk_id)
        if info:
            drives.append(info)

    return drives


def get_drive_info(disk_id: str) -> Optional[DriveInfo]:
    """Get detailed info about a specific disk."""
    result = subprocess.run(
        ["diskutil", "info", "-plist", disk_id],
        capture_output=True, text=True, timeout=10
    )
    if result.returncode != 0:
        return None

    import plistlib
    try:
        plist = plistlib.loads(result.stdout.encode())
    except Exception:
        return None

    # Safety: reject internal drives
    if plist.get("Internal", False):
        logger.warning(f"Rejecting {disk_id}: internal drive")
        return None

    drive = DriveInfo(
        identifier=disk_id,
        name=plist.get("MediaName", "Unknown Drive"),
        size_bytes=plist.get("TotalSize", 0),
        protocol=plist.get("DeviceTreePath", "Unknown"),
    )

    # Get partition list
    drive.partitions = list_partitions(disk_id)
    return drive


def list_partitions(disk_id: str) -> list[PartitionInfo]:
    """List partitions on a drive."""
    result = subprocess.run(
        ["diskutil", "list", "-plist", disk_id],
        capture_output=True, text=True, timeout=10
    )
    if result.returncode != 0:
        return []

    import plistlib
    try:
        plist = plistlib.loads(result.stdout.encode())
    except Exception:
        return []

    partitions = []
    for part_list in plist.get("AllDisksAndPartitions", []):
        for part in part_list.get("Partitions", []):
            p = PartitionInfo(
                identifier=part.get("DeviceIdentifier", ""),
                name=part.get("VolumeName", part.get("Content", "Untitled")),
                type=part.get("Content", "Unknown"),
                size_bytes=part.get("Size", 0),
                mount_point=part.get("MountPoint"),
            )
            partitions.append(p)

    return partitions


def partition_drive(disk_id: str, specs: list[PartitionSpec],
                    progress_log: Optional[str] = None) -> subprocess.Popen:
    """
    Partition a drive according to the given specs.
    Returns a Popen for the privileged operation.

    SAFETY: Caller MUST verify disk_id is external before calling.
    """
    # Build diskutil partitionDisk command
    # Format: diskutil partitionDisk diskN GPT format name size ...
    parts = []
    for spec in specs:
        if spec.purpose == "free":
            parts.append(f'"Free Space" "" {spec.diskutil_size}')
        else:
            parts.append(f'{spec.format} "{spec.name}" {spec.diskutil_size}')

    partitions_str = " ".join(parts)
    cmd = f"diskutil partitionDisk {disk_id} GPT {partitions_str}"

    logger.info(f"Partitioning {disk_id} with {len(specs)} partitions")
    logger.debug(f"Command: {cmd}")

    return run_privileged(cmd, progress_log=progress_log)


def get_volume_mount_point(volume_name: str) -> Optional[str]:
    """Find the mount point for a volume by name."""
    result = subprocess.run(
        ["diskutil", "info", "-plist", volume_name],
        capture_output=True, text=True, timeout=10
    )
    if result.returncode != 0:
        # Try searching by volume name in /Volumes
        from pathlib import Path
        vol = Path("/Volumes") / volume_name
        if vol.exists():
            return str(vol)
        return None

    import plistlib
    try:
        plist = plistlib.loads(result.stdout.encode())
        return plist.get("MountPoint")
    except Exception:
        return None


def verify_external(disk_id: str) -> bool:
    """Double-check that a disk ID is truly an external drive."""
    result = subprocess.run(
        ["diskutil", "info", "-plist", disk_id],
        capture_output=True, text=True, timeout=10
    )
    if result.returncode != 0:
        return False

    import plistlib
    try:
        plist = plistlib.loads(result.stdout.encode())
    except Exception:
        return False

    if plist.get("Internal", True):
        return False

    # Also check it's not the boot volume
    boot_result = subprocess.run(
        ["diskutil", "info", "-plist", "/"],
        capture_output=True, text=True, timeout=10
    )
    if boot_result.returncode == 0:
        boot_plist = plistlib.loads(boot_result.stdout.encode())
        boot_disk = boot_plist.get("ParentWholeDisk", "")
        if boot_disk == disk_id:
            return False

    return True
