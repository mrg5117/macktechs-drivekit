"""
installer.py: macOS installer data model
"""

from dataclasses import dataclass
from typing import Optional

from ..utils.constants import INSTALLER_SIZES, PARTITION_OVERHEAD_GB, OS_NAMES


@dataclass
class InstallerInfo:
    title: str
    version: str
    build: str
    size_kb: int
    deferred: bool = False
    downloaded: bool = False
    app_path: Optional[str] = None

    @property
    def size_gb(self) -> float:
        return round(self.size_kb / 1024 / 1024, 1)

    @property
    def major_version(self) -> str:
        parts = self.version.split(".")
        if int(parts[0]) >= 11:
            return parts[0]
        return f"{parts[0]}.{parts[1]}"

    @property
    def os_name(self) -> str:
        return OS_NAMES.get(self.major_version, self.title.replace("macOS ", ""))

    @property
    def recommended_partition_gb(self) -> int:
        base = INSTALLER_SIZES.get(self.major_version, 16)
        return base + PARTITION_OVERHEAD_GB

    @property
    def display_name(self) -> str:
        return f"{self.title} {self.version}"

    def __str__(self) -> str:
        status = "Downloaded" if self.downloaded else f"{self.size_gb} GB"
        return f"{self.display_name} ({self.build}) [{status}]"
