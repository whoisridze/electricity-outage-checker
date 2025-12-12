# Electricity Outage Checker

CLI tool to check DTEK electricity outage schedules.

## Installation

### Install from PyPI

```bash
pip install electricity-outage-checker
outage-checker --help
```

### Install from source

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
