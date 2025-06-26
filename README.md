# File Renamer

A CLI tool to rename files based on their contents and modification dates. Files are renamed with a prefix of their last modification date followed by a descriptive name intelligently derived from their contents.

## Features

- **Smart Content Analysis**: Recognizes markdown headers, ALL CAPS titles, and meaningful content patterns
- **Multiple File Types**: Supports text files and PDF documents (extracts metadata titles or content)
- **Intelligent Name Selection**: Compares original filenames vs content-based descriptions and chooses the best option
- **Format Standardization**: Converts ALL CAPS text to Capital Case for better readability
- **Configurable Separators**: Choose between dashes (`Project-Report`) or underscores (`Project_Report`)
- **Quality Scoring**: Rates filename quality to preserve good existing names while improving poor ones
- **Dry-run Support**: Preview all changes before applying them
- **Comprehensive Logging**: Verbose mode with detailed processing information

## Installation

1. Make sure you have [uv](https://github.com/astral-sh/uv) installed
2. Clone this repository
3. Install dependencies:

   ```bash
   uv pip install -e ".[dev]"
   ```

## Usage

```bash
# Rename all files in a directory
file-renamer /path/to/directory [OPTIONS]

# Rename a single file
file-renamer /path/to/file.txt [OPTIONS]
```

### Options

- `--dry-run`: Show what would be renamed without making changes
- `--verbose`, `-v`: Enable verbose logging
- `--separator`: Choose separator style (`dash` or `underscore`, default: `dash`)
- `--include-hidden`: Include hidden files (dot files) in processing (default: skip) - only applies to directories
- `--force-rename`: Re-process files that are already renamed (have date prefix)

### Examples

```bash
# Preview changes for a directory with default dash separators
file-renamer ~/Documents/notes --dry-run

# Rename a single file
file-renamer ~/Documents/untitled.txt

# Apply changes to directory with verbose logging
file-renamer ~/Documents/notes --verbose

# Use underscore separators instead of dashes
file-renamer ~/Documents/notes --separator=underscore

# Include hidden files (dot files) in processing
file-renamer ~/Documents/notes --include-hidden

# Force re-processing of already renamed files
file-renamer ~/Documents/notes --force-rename

# Single file examples:
file-renamer document.txt --dry-run
# Output: Would rename: document.txt -> 2024-01-15 - Project-Analysis-Report.txt

file-renamer ~/Downloads/untitled.pdf
# Output: Renamed: untitled.pdf -> 2024-01-15 - Research-Paper-Title.pdf

# Directory examples:
file-renamer ~/Documents/notes --dry-run
# Output:
# Would rename: untitled.txt -> 2024-01-15 - Project-Analysis-Report.txt
# Would rename: MEETING_NOTES.md -> 2024-01-15 - Weekly-Team-Meeting.md
# Would rename: document2.txt -> 2024-01-15 - Project-Analysis-Report-2.txt  # Collision resolved
# Skipping hidden files like .DS_Store, .gitignore (unless --include-hidden is used)
```

## How It Works

### Smart Name Generation

The tool analyzes file content and applies intelligent rules:

1. **Content Analysis**: Looks for meaningful patterns like:
   - Markdown headers (`# Project Report`)
   - ALL CAPS titles (`PROJECT ANALYSIS` → `Project Analysis`)
   - Section headers (`Introduction:`)
   - Meaningful first lines (filters out code imports, comments)

2. **Quality Comparison**: Scores both original filename and content-based description:
   - Preserves good existing names (`Financial_Report_2024.txt`)
   - Improves poor names (`untitled.txt` → content-based name)
   - Uses intelligent scoring based on word count, meaningfulness, and descriptive value

3. **Format Standardization**:
   - Converts ALL CAPS to Capital Case
   - Normalizes separators to chosen style (dash/underscore)
   - Removes consecutive separators and cleans special characters
   - Smart truncation preserves whole words (no more "...Multif.pdf" cut-offs)

4. **Collision Prevention**:
   - Automatically detects filename conflicts and adds counter suffixes (`-2`, `-3`, etc.)
   - Prevents file overwrites when multiple files generate the same name
   - Checks both existing files and files being renamed in the same session

### Supported File Types

- **Text Files** (`.txt`, `.md`, `.py`, etc.): Analyzes content for meaningful titles
- **PDF Files**: Extracts title from metadata or first page text content

## Development

This project uses:

- **Python 3.11+**
- **Click** for CLI interface
- **pypdf** for PDF text extraction
- **uv** for package management
- **pytest** for testing with comprehensive test coverage
- **ruff** for linting and formatting

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
