# Contributing to Macktechs DriveKit

Thanks for your interest in contributing!

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/macktechs-drivekit.git`
3. Create a branch: `git checkout -b feature/your-feature`
4. Install dependencies: `pip3 install -r requirements.txt`
5. Make your changes
6. Test on an external drive (never test on internal drives!)
7. Submit a pull request

## Development Setup

```bash
cd macktechs-drivekit
pip3 install -r requirements.txt
python3 src/main.py
```

## Guidelines

- **Safety first** — This tool operates on disks. Always verify targets are external drives. Never allow operations on internal drives.
- **Test thoroughly** — Disk operations are destructive. Test with cheap USB drives before submitting changes.
- **Keep it simple** — This is a repair shop tool. Reliability beats cleverness.
- **Credit upstream** — If you integrate a new open-source tool, add it to the Acknowledgments section in README.md.

## Reporting Issues

- Include your macOS version, Python version, and drive info
- Paste any error output
- Describe what you expected vs. what happened

## Code Style

- Python 3.9+ compatible
- Follow PEP 8
- Use type hints where practical
- Comment non-obvious logic

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
