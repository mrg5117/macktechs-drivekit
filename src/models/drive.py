"""
drive.py: External drive and partition data models
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PartitionInfo:
    identifier: str
    name: str
    type: str
    size_bytes: int
    mount_point: Optional[str] = None

    @property
    def size_gb(self) -> float:
        return round(self.size_bytes / 1e9, 1)

    @property
    def display_size(self) -> str:
        gb = self.size_gb
        if gb >= 1000:
            return f"{gb / 1000:.1f} TB"
        return f"{gb:.1f} GB"


@dataclass
class PartitionSpec:
    name: str
    format: str          # "JHFS+", "APFS", "ExFAT", "Free Space"
    size_gb: float       # 0 = use remainder
    purpose: str         # "installer", "bootable_os", "tools", "free"
    installer_version: Optional[str] = None

    @property
    def size_bytes(self) -> int:
        return int(self.size_gb * 1e9)

    @property
    def diskutil_size(self) -> str:
        if self.size_gb == 0:
            return "R"
        return f"{self.size_gb:.0f}g"


@dataclass
class DriveInfo:
    identifier: str          # "disk2"
    name: str                # "CT1000BX500SSD1"
    size_bytes: int
    protocol: str            # "USB"
    partitions: list[PartitionInfo] = field(default_factory=list)

    @property
    def size_gb(self) -> float:
        return round(self.size_bytes / 1e9, 1)

    @property
    def display_size(self) -> str:
        gb = self.size_gb
        if gb >= 1000:
            return f"{gb / 1000:.1f} TB"
        return f"{gb:.1f} GB"

    @property
    def display_name(self) -> str:
        return f"{self.name} ({self.display_size}) — {self.identifier}"

    @property
    def is_external(self) -> bool:
        return True  # We only ever list external drives
