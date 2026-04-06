"""
profile.py: Drive layout profile data model
"""

from dataclasses import dataclass, field
import json
from pathlib import Path

from .drive import PartitionSpec


@dataclass
class DriveProfile:
    name: str
    description: str
    min_drive_size_gb: float
    partitions: list[PartitionSpec] = field(default_factory=list)

    def total_size_gb(self) -> float:
        return sum(p.size_gb for p in self.partitions if p.size_gb > 0)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "min_drive_size_gb": self.min_drive_size_gb,
            "partitions": [
                {
                    "name": p.name,
                    "format": p.format,
                    "size_gb": p.size_gb,
                    "purpose": p.purpose,
                    "installer_version": p.installer_version,
                }
                for p in self.partitions
            ],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DriveProfile":
        partitions = [
            PartitionSpec(
                name=p["name"],
                format=p["format"],
                size_gb=p["size_gb"],
                purpose=p["purpose"],
                installer_version=p.get("installer_version"),
            )
            for p in data["partitions"]
        ]
        return cls(
            name=data["name"],
            description=data["description"],
            min_drive_size_gb=data["min_drive_size_gb"],
            partitions=partitions,
        )

    def save(self, path: Path) -> None:
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: Path) -> "DriveProfile":
        with open(path) as f:
            return cls.from_dict(json.load(f))
