"""
constants.py: Application-wide constants for Macktechs DriveKit
"""

APP_NAME = "Macktechs DriveKit"
APP_VERSION = "0.1.0"
APP_BUNDLE_ID = "com.macktechs.drivekit"

# Minimum partition sizes (GB) for each macOS installer
INSTALLER_SIZES = {
    "10.13": 6,    # High Sierra
    "10.14": 8,    # Mojave
    "10.15": 10,   # Catalina
    "11":    14,   # Big Sur
    "12":    14,   # Monterey
    "13":    14,   # Ventura
    "14":    15,   # Sonoma
    "15":    16,   # Sequoia
}

# Friendly names for macOS versions
OS_NAMES = {
    "10.13": "High Sierra",
    "10.14": "Mojave",
    "10.15": "Catalina",
    "11": "Big Sur",
    "12": "Monterey",
    "13": "Ventura",
    "14": "Sonoma",
    "15": "Sequoia",
}

# Recommended partition size overhead (GB added to installer size)
PARTITION_OVERHEAD_GB = 2

# Minimum drive sizes for profiles
MIN_DRIVE_256 = 240
MIN_DRIVE_500 = 460
MIN_DRIVE_1TB = 900

# Default tools partition size (GB)
DEFAULT_TOOLS_SIZE_GB = 20

# Default bootable OS partition size (GB)
DEFAULT_BOOT_OS_SIZE_GB = 40

# Paths
INSTALLERS_DIR = "/Applications"
