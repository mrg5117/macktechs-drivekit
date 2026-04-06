"""
deploy_profile.py: Deployment profiles for pre-configuring macOS installs
(username, password, computer name, etc.)
"""

import logging
import os
import plistlib
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import json

logger = logging.getLogger("drivekit.deploy")


@dataclass
class DeployProfile:
    name: str = "Default"
    full_name: str = ""
    username: str = ""
    password: str = ""
    computer_name: str = ""
    auto_login: bool = False
    skip_setup_assistant: bool = True
    timezone: str = "America/New_York"
    language: str = "en"
    region: str = "US"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "full_name": self.full_name,
            "username": self.username,
            "password": self.password,
            "computer_name": self.computer_name,
            "auto_login": self.auto_login,
            "skip_setup_assistant": self.skip_setup_assistant,
            "timezone": self.timezone,
            "language": self.language,
            "region": self.region,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DeployProfile":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def save(self, path: Path) -> None:
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: Path) -> "DeployProfile":
        with open(path) as f:
            return cls.from_dict(json.load(f))


def get_builtin_profiles() -> list[DeployProfile]:
    """Return pre-built deployment profiles."""
    return [
        DeployProfile(
            name="Macktechs Tech Bench",
            full_name="Macktechs",
            username="macktechs",
            password="macktechs",
            computer_name="Macktechs-Service",
            auto_login=True,
            skip_setup_assistant=True,
        ),
        DeployProfile(
            name="Client Handoff",
            full_name="",
            username="",
            password="",
            computer_name="",
            auto_login=False,
            skip_setup_assistant=False,
        ),
        DeployProfile(
            name="Custom",
            full_name="",
            username="",
            password="",
            computer_name="",
            auto_login=False,
            skip_setup_assistant=True,
        ),
    ]


def generate_firstboot_pkg(profile: DeployProfile, output_dir: str) -> Optional[str]:
    """
    Generate a first-boot package that creates the user account
    and applies settings when macOS first boots.
    """
    if not profile.username or not profile.password:
        logger.info("No username/password set, skipping firstboot package")
        return None

    work_dir = tempfile.mkdtemp(prefix="drivekit_pkg_")
    scripts_dir = Path(work_dir) / "scripts"
    scripts_dir.mkdir()

    # Create postinstall script
    postinstall = scripts_dir / "postinstall"
    script_lines = [
        "#!/bin/bash",
        "# Macktechs DriveKit - First Boot Configuration",
        f"# Profile: {profile.name}",
        "",
    ]

    # Create user account
    script_lines.extend([
        f'# Create user account',
        f'sysadminctl -addUser "{profile.username}" '
        f'-fullName "{profile.full_name}" '
        f'-password "{profile.password}" -admin',
        "",
    ])

    # Set computer name
    if profile.computer_name:
        script_lines.extend([
            f'scutil --set ComputerName "{profile.computer_name}"',
            f'scutil --set LocalHostName "{profile.computer_name}"',
            f'scutil --set HostName "{profile.computer_name}"',
            "",
        ])

    # Set timezone
    script_lines.extend([
        f'systemsetup -settimezone "{profile.timezone}"',
        "",
    ])

    # Skip Setup Assistant
    if profile.skip_setup_assistant:
        script_lines.extend([
            '# Skip Setup Assistant for all users',
            'for user_home in /Users/*/; do',
            '  user=$(basename "$user_home")',
            '  if [ "$user" != "Shared" ] && [ "$user" != ".localized" ]; then',
            '    touch "$user_home/.AppleSetupDone"',
            '  fi',
            'done',
            'touch /var/db/.AppleSetupDone',
            "",
        ])

    # Auto-login
    if profile.auto_login:
        script_lines.extend([
            f'# Enable auto-login',
            f'defaults write /Library/Preferences/com.apple.loginwindow autoLoginUser "{profile.username}"',
            "",
        ])

    script_lines.append("exit 0")

    postinstall.write_text("\n".join(script_lines))
    os.chmod(postinstall, 0o755)

    # Build the pkg
    pkg_path = Path(output_dir) / f"MacktechsSetup-{profile.name.replace(' ', '_')}.pkg"
    try:
        result = subprocess.run([
            "pkgbuild",
            "--nopayload",
            "--scripts", str(scripts_dir),
            "--identifier", f"com.macktechs.drivekit.setup.{profile.username}",
            "--version", "1.0",
            str(pkg_path),
        ], capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            logger.info(f"Created firstboot package: {pkg_path}")
            return str(pkg_path)
        else:
            logger.error(f"pkgbuild failed: {result.stderr}")
            return None
    except Exception as e:
        logger.error(f"Failed to create package: {e}")
        return None
    finally:
        import shutil
        shutil.rmtree(work_dir, ignore_errors=True)


def save_profiles_to_volume(profiles: list[DeployProfile], volume: str) -> None:
    """Save deployment profiles to a volume for later use."""
    dest = Path(volume) / "DriveKit" / "profiles"
    dest.mkdir(parents=True, exist_ok=True)
    for p in profiles:
        p.save(dest / f"{p.name.replace(' ', '_')}.json")
    logger.info(f"Saved {len(profiles)} profiles to {dest}")


def load_saved_profiles() -> list[DeployProfile]:
    """Load any previously saved custom profiles."""
    config_dir = Path.home() / ".config" / "macktechs-drivekit" / "profiles"
    if not config_dir.exists():
        return []
    profiles = []
    for f in config_dir.glob("*.json"):
        try:
            profiles.append(DeployProfile.load(f))
        except Exception as e:
            logger.warning(f"Failed to load profile {f}: {e}")
    return profiles


def save_custom_profile(profile: DeployProfile) -> None:
    """Save a custom profile to the config directory."""
    config_dir = Path.home() / ".config" / "macktechs-drivekit" / "profiles"
    config_dir.mkdir(parents=True, exist_ok=True)
    profile.save(config_dir / f"{profile.name.replace(' ', '_')}.json")
    logger.info(f"Saved profile: {profile.name}")
