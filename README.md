<div align="center">

# Electricity Outage Checker

[![Release version](https://img.shields.io/github/v/release/whoisridze/electricity-outage-checker?color=brightgreen&label=Release&style=for-the-badge)](https://github.com/whoisridze/electricity-outage-checker/releases/latest "Latest Release")
[![PyPI](https://img.shields.io/badge/-PyPI-blue.svg?logo=pypi&labelColor=555555&style=for-the-badge)](https://pypi.org/project/electricity-outage-checker "PyPI")
[![Python](https://img.shields.io/pypi/pyversions/electricity-outage-checker?logo=python&labelColor=555555&style=for-the-badge)](https://pypi.org/project/electricity-outage-checker "Python version")

*CLI tool to check DTEK electricity outage schedules*

</div>

## Installation

### Option 1: Download Executable (Recommended)

Standalone executables are automatically built by GitHub Actions for each release.

1. Go to [**Releases**](https://github.com/whoisridze/electricity-outage-checker/releases/latest)
2. Download the executable for your platform:
   - **macOS**: `outage-checker-macos` (universal binary for Intel & Apple Silicon)
   - **Windows**: `outage-checker-windows.exe`
   - **Linux**: `outage-checker-linux`
3. Make it executable (macOS/Linux only):
   ```bash
   chmod +x outage-checker-macos
   ```
4. Run it:
   ```bash
   ./outage-checker-macos --help
   ```

**Want to build the executable yourself?**
```bash
# Install dependencies
uv sync

# Build executable
uv run pyinstaller outage-checker.spec

# The executable will be in dist/outage-checker
./dist/outage-checker --help
```

### Option 2: Install from PyPI

```bash
pip install electricity-outage-checker
outage-checker --help
```

### Option 3: Install from Source

```bash
git clone https://github.com/whoisridze/electricity-outage-checker.git
cd electricity-outage-checker
uv sync
uv run outage-checker --help
```

## Usage

```bash
# Check outage schedule for an address
outage-checker check "<city>, <street>, <house>"

# Set a default address
outage-checker set-address "<city>, <street>, <house>"

# Check using default address
outage-checker check

# List available cities
outage-checker list-cities

# List streets in a city
outage-checker list-streets "<city>"

# List houses on a street
outage-checker list-houses "<city>" "<street>"

# Show version
outage-checker --version
```

## Development

```bash
# Install dev dependencies
uv sync

# Run linter
uv run ruff check .

# Format code
uv run ruff format .
uv run ruff check --fix .

# Run type checker
uv run mypy src/

# Build executable
uv run pyinstaller outage-checker.spec
```

## Project Structure

```
electricity-outage-checker/
├── src/
│   └── electricity_outage_checker/
│       ├── __init__.py
│       ├── cli.py          # CLI entry point
│       ├── client.py       # DTEK API client
│       ├── config.py       # User configuration
│       ├── models.py       # Data models
│       └── py.typed        # PEP 561 marker
├── pyproject.toml          # Project configuration
└── README.md
```

## License

MIT
