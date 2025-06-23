# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python CLI tool called "file-renamer" that renames files based on their modification dates and content. Files are renamed with a date prefix (YYYY-MM-DD) followed by a descriptive name derived from their first line of content.

## Development Commands

### Package Management

- Install dependencies: `uv pip install -e ".[dev]"`

- The project uses `uv` for package management

### Testing

- Run all tests: `pytest`

- Run specific test: `pytest tests/test_cli.py::test_function_name`

### Code Quality

- Run linting: `ruff check .`

- Run formatting: `ruff format .`

- Ruff configuration is in pyproject.toml with line length 120, Python 3.11+ target

## Architecture

### Core Components

- `file_renamer/cli.py`: Main CLI module containing:

  - `get_file_description()`: Intelligently chooses between original filename and content-based description

  - `_extract_text_description()`: Analyzes text files for meaningful titles (markdown headers, ALL CAPS titles, etc.)

  - `_extract_pdf_description()`: Extracts PDF metadata titles or first page text

  - `_choose_best_description()`: Scores and compares original vs content-based names

  - `_score_description()`: Rates description quality (0-10 scale)

  - `rename_files()`: Core renaming logic with dry-run support

  - `main()`: Click-based CLI entry point

### File Naming Pattern

Files are renamed as: `YYYY-MM-DD - {description}.{extension}`

- Date comes from file modification time

- Description is sanitized first line of file content

- Non-alphanumeric characters (except spaces, hyphens, underscores) become underscores

### CLI Usage

- `file-renamer /path/to/directory [OPTIONS]`

- `--dry-run`: Preview changes without applying

- `--verbose/-v`: Enable debug logging

- `--separator`: Choose separator style (`dash` or `underscore`, default: `dash`)

- `--include-hidden`: Include hidden files (dot files) in processing (default: skip)

### Testing Structure

- Tests use pytest with fixtures for temporary files

- Mocking for unreadable file scenarios

- Time freezing for consistent timestamp testing

- Type hints with TYPE_CHECKING import pattern

### Dependencies

- click: CLI framework

- python-dateutil: Date parsing utilities

- python-dotenv: Environment variable handling

- pypdf: PDF text extraction for PDF file support

- Development: pytest, pytest-mock, ruff

### Supported File Types

- Text files: Intelligently analyzes content for meaningful titles (markdown headers, ALL CAPS titles, meaningful first lines)

- PDF files: Extracts title from metadata or first page text content

### Smart Name Generation

- Compares original filename quality vs content-based description

- Preserves good existing filenames (e.g., "Financial_Report_2024.txt")

- Improves poor filenames (e.g., "untitled.txt" → content-based name)

- Recognizes patterns like markdown headers (`# Title`), ALL CAPS titles, section headers

- Converts ALL CAPS text to Capital Case for better readability

- Filters out uninformative content (import statements, comments, generic patterns)

- Scores descriptions based on word count, meaningfulness, and descriptive value

- Configurable separator preference: dashes (`Project-Report`) or underscores (`Project_Report`)

- Normalizes all separators to chosen style and removes consecutive separators

- Prevents filename collisions by adding counter suffixes (`-2`, `-3`, etc.) when multiple files would generate the same name