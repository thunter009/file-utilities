# File Renamer

A CLI tool to rename files based on their contents and modification dates. Files are renamed with a prefix of their last modification date followed by a descriptive name derived from their contents.

## Features

- Renames files using modification date as prefix
- Generates descriptive names from file contents
- Supports dry-run mode for previewing changes

## Installation

1. Make sure you have [uv](https://github.com/astral-sh/uv) installed
2. Clone this repository
3. Install dependencies:

   ```bash
   uv pip install -e ".[dev]"
   ```

## Usage

```bash
file-renamer /path/to/directory [OPTIONS]
```

### Options

- `--dry-run`: Show what would be renamed without making changes
- `--verbose`, `-v`: Enable verbose logging

### Example

```bash
# Preview changes
file-renamer ~/Documents/notes --dry-run

# Apply changes with verbose logging
file-renamer ~/Documents/notes --verbose
```

## Development

This project uses:

- Python 3.11+
- Click for CLI interface
- uv for package management
- pytest for testing
- ruff for linting and formatting

### Development Setup

1. Install development dependencies:

   ```bash
   uv pip install -e ".[dev]"
   ```

2. Run tests:

   ```bash
   pytest
   ```

3. Run linting:

   ```bash
   ruff check .
   ```

4. Run formatting:

   ```bash
   ruff format .
   ```

### Project Structure

```plaintext
file-renamer/
├── file_renamer/        # Source code
│   ├── __init__.py
│   ├── __main__.py
│   └── cli.py
├── tests/              # Test files
│   ├── __init__.py
│   └── test_cli.py
├── pyproject.toml     # Project configuration
└── README.md         # Documentation
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## License

MIT
