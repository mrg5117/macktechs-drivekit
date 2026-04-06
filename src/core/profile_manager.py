"""
profile_manager.py: Built-in and custom drive profiles
"""

import json
import logging
from pathlib import Path

from ..models.drive import PartitionSpec
from ..models.profile import DriveProfile

logger = logging.getLogger("drivekit.profile")


def get_builtin_profiles() -> list[DriveProfile]:
    """Return the built-in drive profiles."""
    return [
        _profile_modern_256(),
        _profile_full_service_500(),
        _profile_full_service_1tb(),
        _profile_deployment_only(),
    ]


def _profile_modern_256() -> DriveProfile:
    return DriveProfile(
        name="Modern Only (256 GB)",
        description="Monterey through Sequoia — ideal for newer Macs",
        min_drive_size_gb=240,
        partitions=[
            PartitionSpec("Install macOS Monterey", "JHFS+", 16, "installer", "12"),
            PartitionSpec("Install macOS Ventura", "JHFS+", 16, "installer", "13"),
            PartitionSpec("Install macOS Sonoma", "JHFS+", 17, "installer", "14"),
            PartitionSpec("Install macOS Sequoia", "JHFS+", 18, "installer", "15"),
            PartitionSpec("Tools", "JHFS+", 15, "tools"),
            PartitionSpec("Free Space", "Free Space", 0, "free"),
        ],
    )


def _profile_full_service_500() -> DriveProfile:
    return DriveProfile(
        name="Full Service (500 GB)",
        description="High Sierra through Sequoia + bootable OS + tools — the works",
        min_drive_size_gb=460,
        partitions=[
            PartitionSpec("Boot Catalina", "JHFS+", 25, "bootable_os", "10.15"),
            PartitionSpec("Install macOS High Sierra", "JHFS+", 8, "installer", "10.13"),
            PartitionSpec("Install macOS Mojave", "JHFS+", 10, "installer", "10.14"),
            PartitionSpec("Install macOS Catalina", "JHFS+", 12, "installer", "10.15"),
            PartitionSpec("Install macOS Big Sur", "JHFS+", 16, "installer", "11"),
            PartitionSpec("Install macOS Monterey", "JHFS+", 16, "installer", "12"),
            PartitionSpec("Install macOS Ventura", "JHFS+", 16, "installer", "13"),
            PartitionSpec("Install macOS Sonoma", "JHFS+", 17, "installer", "14"),
            PartitionSpec("Install macOS Sequoia", "JHFS+", 18, "installer", "15"),
            PartitionSpec("Tools", "JHFS+", 20, "tools"),
            PartitionSpec("Recovery", "JHFS+", 80, "tools"),
            PartitionSpec("Free Space", "Free Space", 0, "free"),
        ],
    )


def _profile_full_service_1tb() -> DriveProfile:
    return DriveProfile(
        name="Full Service (1 TB)",
        description="Everything + large recovery workspace + multiple boot OS partitions",
        min_drive_size_gb=900,
        partitions=[
            PartitionSpec("Boot Catalina", "JHFS+", 30, "bootable_os", "10.15"),
            PartitionSpec("Boot Monterey", "JHFS+", 40, "bootable_os", "12"),
            PartitionSpec("Install macOS High Sierra", "JHFS+", 8, "installer", "10.13"),
            PartitionSpec("Install macOS Mojave", "JHFS+", 10, "installer", "10.14"),
            PartitionSpec("Install macOS Catalina", "JHFS+", 12, "installer", "10.15"),
            PartitionSpec("Install macOS Big Sur", "JHFS+", 16, "installer", "11"),
            PartitionSpec("Install macOS Monterey", "JHFS+", 16, "installer", "12"),
            PartitionSpec("Install macOS Ventura", "JHFS+", 16, "installer", "13"),
            PartitionSpec("Install macOS Sonoma", "JHFS+", 17, "installer", "14"),
            PartitionSpec("Install macOS Sequoia", "JHFS+", 18, "installer", "15"),
            PartitionSpec("Tools", "JHFS+", 30, "tools"),
            PartitionSpec("Recovery", "JHFS+", 150, "tools"),
            PartitionSpec("Free Space", "Free Space", 0, "free"),
        ],
    )


def _profile_deployment_only() -> DriveProfile:
    return DriveProfile(
        name="MDS Deployment (256 GB)",
        description="Focused on T2/Apple Silicon deployment with MDS",
        min_drive_size_gb=240,
        partitions=[
            PartitionSpec("Install macOS Ventura", "JHFS+", 16, "installer", "13"),
            PartitionSpec("Install macOS Sonoma", "JHFS+", 17, "installer", "14"),
            PartitionSpec("Install macOS Sequoia", "JHFS+", 18, "installer", "15"),
            PartitionSpec("MDS Data", "JHFS+", 10, "tools"),
            PartitionSpec("Free Space", "Free Space", 0, "free"),
        ],
    )


def suggest_profile(drive_size_gb: float) -> DriveProfile:
    """Suggest the best profile for a given drive size."""
    profiles = get_builtin_profiles()
    suitable = [p for p in profiles if p.min_drive_size_gb <= drive_size_gb]
    if not suitable:
        return profiles[0]  # Return smallest profile
    # Return the largest profile that fits
    return max(suitable, key=lambda p: p.min_drive_size_gb)
