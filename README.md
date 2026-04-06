# Macktechs DriveKit

A macOS utility for building multi-boot installer drives for Mac repair technicians. Create fully loaded service drives with every macOS version, diagnostic tools, and deployment support — all from one app.

## Features

- **Installer Management** — Download and manage macOS installers from High Sierra through Sequoia
- **Multi-Boot Drive Builder** — Partition and flash multiple macOS installers to a single external drive
- **Drive Profiles** — Pre-configured templates for common drive layouts (256GB, 500GB, 1TB)
- **Bootable OS Partition** — Create a working macOS environment for bench diagnostics
- **Tools Partition** — Pre-load free repair and diagnostic utilities
- **MDS Integration** — Set up drives for Mac Deploy Stick workflows on T2/Apple Silicon Macs
- **OCLP Awareness** — Model compatibility info for unsupported Macs via OpenCore Legacy Patcher

## Screenshots

*Coming soon*

## Requirements

- macOS 12 Monterey or later
- Python 3.9+
- Administrator privileges (for disk operations)
- External drive (256GB minimum, 1TB recommended)

## Installation

### From Release

Download the latest `.dmg` from [Releases](https://github.com/mrg5117/macktechs-drivekit/releases).

### From Source

```bash
git clone https://github.com/mrg5117/macktechs-drivekit.git
cd macktechs-drivekit
pip3 install -r requirements.txt
python3 src/main.py
```

## Recommended Drive Sizes

| Drive Size | What Fits |
|---|---|
| **256 GB** | 4-5 installers (Monterey+), small tools partition |
| **500 GB** | All installers (High Sierra-Sequoia), bootable OS, tools, free space |
| **1 TB** | Everything + multiple bootable OS partitions, large recovery workspace |

## Usage

1. Launch Macktechs DriveKit
2. Connect an external drive
3. Select a drive profile or customize your layout
4. Choose which macOS versions to include
5. Click **Build Drive** and let it run

## Acknowledgments & Credits

Macktechs DriveKit stands on the shoulders of these excellent open-source projects:

### Core Inspiration & Integration

- **[Mist](https://github.com/ninxsoft/Mist)** by ninxsoft — macOS installer download engine (MIT License)
- **[mist-cli](https://github.com/ninxsoft/mist-cli)** by ninxsoft — CLI backend for installer downloads (MIT License)
- **[OpenCore Legacy Patcher](https://github.com/dortania/OpenCore-Legacy-Patcher)** by Dortania — Unsupported Mac patching (BSD 3-Clause License)
- **[MDS (Mac Deploy Stick)](https://twocanoes.com/products/mac/mds/)** by Twocanoes Software — Mac deployment workflows (BSD License)
- **[macUSB](https://github.com/Kruszoneq/macUSB)** by Kruszoneq — Bootable USB creator with legacy support (MIT License)
- **[TINU](https://github.com/ITzTravelInTime/TINU)** by ITzTravelInTime — createinstallmedia GUI wrapper (GPL-2.0)
- **[installinstallmacos.py](https://github.com/munki/macadmin-scripts)** by Greg Neagle / Munki Project — macOS installer scripting

### Bundled & Recommended Tools

#### Security (Objective-See)
- **[LuLu](https://github.com/objective-see/LuLu)** — Free macOS firewall (GPL-3.0)
- **[KnockKnock](https://github.com/objective-see/KnockKnock)** — Persistent software scanner (GPL-3.0)
- **[BlockBlock](https://github.com/objective-see/BlockBlock)** — Persistence monitor (GPL-3.0)

#### Diagnostics & Monitoring
- **[Stats](https://github.com/exelban/stats)** by exelban — System monitor (MIT License)
- **[smartmontools](https://www.smartmontools.org/)** — S.M.A.R.T. disk health monitoring (GPL-2.0)
- **[AHTFinder](https://github.com/MaxTechnics/AHTFinder)** — Apple Hardware Test locator

#### Data Recovery
- **[TestDisk / PhotoRec](https://www.cgsecurity.org/wiki/TestDisk)** by CGSecurity — Partition and file recovery (GPL-2.0)
- **[drat](https://github.com/jivanpal/drat)** — APFS data recovery (GPL-3.0)

#### System Maintenance
- **[Pearcleaner](https://github.com/alienator88/Pearcleaner)** by alienator88 — App uninstaller (Apache 2.0)
- **[mac-cleanup-py](https://github.com/mac-cleanup/mac-cleanup-py)** — System cleanup scripts (Apache 2.0)

#### Network
- **[Trippy](https://github.com/fujiapple852/trippy)** — Network diagnostics (Apache 2.0)

#### Provisioning
- **[dockutil](https://github.com/kcrawford/dockutil)** — Dock management (Apache 2.0)
- **[tccutil](https://github.com/jacobsalmela/tccutil)** — TCC permissions management (GPL-2.0)

### macOS Community Resources
- **[awesome-macadmin-tools](https://github.com/smashism/awesome-macadmin-tools)** — Curated Mac admin tool list
- **[open-source-mac-os-apps](https://github.com/serhii-londar/open-source-mac-os-apps)** — Open source macOS apps directory

## License

MIT License — see [LICENSE](LICENSE) for details.

## Contributing

Contributions welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Author

Built by [Macktechs](https://macktechs.com) — Mac repair and IT services.
