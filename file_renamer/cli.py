"""CLI module for file renaming operations.

This module provides functionality to rename files based on their modification dates
and contents, following a consistent naming pattern.
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import NoReturn

import click
from pypdf import PdfReader

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger(__name__)


def get_file_description(file_path: Path, separator: str = "dash") -> str:
    """Generate a descriptive name based on file contents.

    ### Args:
        file_path: Path to the file to generate description for.
        separator: Preferred separator style for filename formatting.

    ### Returns:
        A string containing a safe, descriptive name based on the file's contents.
        If the file cannot be read, returns the original filename without extension.

    ### Example:
        ```python
        description = get_file_description(Path("document.txt"), "dash")
        # Returns: "First-line-of-the-document"
        ```
    """
    original_name = os.path.splitext(file_path.name)[0]

    try:
        # Handle PDF files
        if file_path.suffix.lower() == ".pdf":
            content_description = _extract_pdf_description(file_path, separator)
        else:
            # Handle text files
            content_description = _extract_text_description(file_path, separator)

        # Choose the best description between original and content-based
        return _choose_best_description(original_name, content_description, separator)

    except Exception as e:
        logger.warning(f"Could not read file {file_path}: {str(e)}")
        return original_name


def _extract_text_description(file_path: Path, separator: str = "dash") -> str:
    """Extract description from text file with improved logic.

    ### Args:
        file_path: Path to the text file.
        separator: Preferred separator style for filename formatting.

    ### Returns:
        A string containing a descriptive name based on the file's content.
    """
    with open(file_path, encoding="utf-8") as f:
        content = f.read(1000)  # Read more content for better analysis

    lines = [line.strip() for line in content.split("\n") if line.strip()]

    if not lines:
        return os.path.splitext(file_path.name)[0]

    # Try to find the most descriptive line
    candidates = []

    # Look for title-like patterns (markdown headers, etc.)
    for line in lines[:10]:  # Check first 10 lines
        if line.startswith("#"):
            # Markdown header
            candidates.append((line.lstrip("#").strip(), 10))
        elif line.isupper() and len(line.split()) <= 6:
            # ALL CAPS title - convert to Capital Case
            title_case = line.title()
            candidates.append((title_case, 8))
        elif line.endswith(":") and len(line.split()) <= 4:
            # Section header ending with colon
            candidates.append((line.rstrip(":"), 6))

    # If no special patterns, look for meaningful first lines
    if not candidates:
        for line in lines[:3]:  # Check first 3 lines
            if _is_meaningful_line(line):
                candidates.append((line, 5))

    # Fall back to first line if nothing better found
    if not candidates:
        candidates.append((lines[0], 1))

    # Choose the best candidate
    best_text = max(candidates, key=lambda x: x[1])[0]

    # Clean up and return
    cleaned = _clean_filename(best_text, separator)
    return _smart_truncate(cleaned)


def _is_meaningful_line(line: str) -> bool:
    """Check if a line contains meaningful content for a filename.

    ### Args:
        line: The line to evaluate.

    ### Returns:
        True if the line appears to contain meaningful content.
    """
    # Skip common uninformative patterns
    uninformative_patterns = [
        # Common code patterns
        r"^import\s+",
        r"^from\s+.*import",
        r"^#.*",
        r"^//.*",
        r"^/\*.*",
        r"^\s*$",
        # Common document patterns
        r"^chapter\s+\d+$",
        r"^section\s+\d+$",
        r"^page\s+\d+$",
        r"^\d+\.$",  # Just numbers
        r"^[IVXivx]+\.$",  # Roman numerals
    ]

    import re

    line_lower = line.lower().strip()

    for pattern in uninformative_patterns:
        if re.match(pattern, line_lower):
            return False

    # Prefer lines with actual words
    words = line.split()
    if len(words) < 2 or len(words) > 10:
        return False

    # Check for reasonable word length
    avg_word_length = sum(len(word) for word in words) / len(words)
    if avg_word_length < 2:
        return False

    return True


def _clean_filename(text: str, separator: str = "dash") -> str:
    """Clean text to make it safe for use in filenames.

    ### Args:
        text: The text to clean.
        separator: Preferred separator style ("dash" or "underscore").

    ### Returns:
        Cleaned text safe for filenames.
    """
    # Choose separator character
    sep_char = "-" if separator == "dash" else "_"

    # Replace spaces and unsafe characters with separator
    cleaned = ""
    for char in text:
        if char.isalnum():
            cleaned += char
        elif char in (" ", "-", "_"):
            # Convert all separators to preferred style
            cleaned += sep_char
        else:
            # Replace other characters with separator
            cleaned += sep_char

    # Remove consecutive separators and trim
    import re

    pattern = f"\\{sep_char}+"
    cleaned = re.sub(pattern, sep_char, cleaned)
    cleaned = cleaned.strip(sep_char)

    return cleaned


def _smart_truncate(text: str, max_length: int = 80) -> str:
    """Truncate text while preserving whole words.

    ### Args:
        text: The text to truncate.
        max_length: Maximum length for the truncated text.

    ### Returns:
        Truncated text that doesn't cut off words mid-way.
    """
    if len(text) <= max_length:
        return text

    # Find the last space before the max_length
    truncated = text[:max_length]
    last_space = truncated.rfind(" ")
    last_dash = truncated.rfind("-")
    last_underscore = truncated.rfind("_")

    # Use the rightmost word boundary
    last_boundary = max(last_space, last_dash, last_underscore)

    if last_boundary > max_length * 0.7:  # Only truncate if we keep at least 70% of desired length
        return text[:last_boundary]
    else:
        # If truncating would remove too much, just use character limit
        return text[:max_length]


def _choose_best_description(original_name: str, content_description: str, separator: str = "dash") -> str:
    """Choose the better description between original filename and content-based.

    ### Args:
        original_name: Original filename without extension.
        content_description: Description extracted from content.
        separator: Preferred separator style for formatting.

    ### Returns:
        The better description to use.
    """
    # Clean and score both descriptions
    cleaned_original = _clean_filename(original_name, separator)
    cleaned_content = _clean_filename(content_description, separator)

    original_score = _score_description(cleaned_original)
    content_score = _score_description(cleaned_content)

    logger.debug(
        f"Original '{cleaned_original}' score: {original_score}, Content '{cleaned_content}' score: {content_score}"
    )

    # Use content description if it's significantly better
    if content_score > original_score + 2:
        return cleaned_content

    # Use original if it's already good and content isn't much better
    if original_score >= 5 and content_score <= original_score + 1:
        return cleaned_original

    # Default to content description for borderline cases
    return cleaned_content if content_score >= original_score else cleaned_original


def _score_description(description: str) -> int:
    """Score a description for usefulness as a filename.

    ### Args:
        description: The description to score (can be space or separator-delimited).

    ### Returns:
        Score from 0-10, higher is better.
    """
    if not description:
        return 0

    score = 0
    # Split on spaces, dashes, or underscores to get words
    import re

    words = re.split(r"[\s\-_]+", description)
    words = [w for w in words if w]  # Remove empty strings

    # Length scoring
    if 2 <= len(words) <= 6:
        score += 3
    elif len(words) == 1:
        score += 1

    # Word quality
    for word in words:
        if len(word) >= 3:
            score += 1
        if word.isalpha():  # Prefer alphabetic words
            score += 1

    # Penalize generic patterns
    generic_patterns = ["untitled", "document", "file", "new", "copy", "temp", "test"]
    if any(pattern in description.lower() for pattern in generic_patterns):
        score -= 2

    # Bonus for descriptive words
    descriptive_words = ["report", "analysis", "summary", "guide", "manual", "proposal", "plan"]
    if any(word in description.lower() for word in descriptive_words):
        score += 2

    return max(0, min(10, score))


def _extract_pdf_description(file_path: Path, separator: str = "dash") -> str:
    """Extract description from PDF file.

    ### Args:
        file_path: Path to the PDF file.
        separator: Preferred separator style for filename formatting.

    ### Returns:
        A string containing a safe, descriptive name based on the PDF's content.
    """
    try:
        with open(file_path, "rb") as f:
            reader = PdfReader(f)

            # Try to get title from metadata first
            if reader.metadata and reader.metadata.title:
                title = reader.metadata.title.strip()
                if title:
                    # Convert ALL CAPS to title case
                    if title.isupper():
                        title = title.title()
                    cleaned = _clean_filename(title, separator)
                    return _smart_truncate(cleaned)

            # Fall back to extracting text from first page
            if len(reader.pages) > 0:
                first_page = reader.pages[0]
                text = first_page.extract_text()

                # Get first meaningful line of text
                lines = [line.strip() for line in text.split("\n") if line.strip()]
                if lines:
                    first_line = lines[0]
                    # Convert ALL CAPS to title case
                    if first_line.isupper():
                        first_line = first_line.title()
                    cleaned = _clean_filename(first_line, separator)
                    return _smart_truncate(cleaned)

    except Exception as e:
        logger.warning(f"Could not extract PDF content from {file_path}: {str(e)}")

    # Return filename without extension as fallback
    return os.path.splitext(file_path.name)[0]


def rename_single_file(
    file_path: Path | str, dry_run: bool = False, separator: str = "dash", force_rename: bool = False
) -> None:
    """Rename a single file based on its modification date and contents.

    ### Args:
        file_path: Path to the file to rename.
        dry_run: If True, only show what would be renamed without making changes.
        separator: Preferred separator style ("dash" or "underscore").
        force_rename: If True, re-process files that are already renamed.

    ### Example:
        ```python
        # Preview changes for a single file
        rename_single_file("document.txt", dry_run=True)

        # Rename a single file
        rename_single_file("document.txt")
        ```
    """
    file_path = Path(file_path)

    if not file_path.exists():
        logger.error(f"File {file_path} does not exist")
        return

    if not file_path.is_file():
        logger.error(f"{file_path} is not a file")
        return

    try:
        # Get modification time
        mod_time = datetime.fromtimestamp(file_path.stat().st_mtime)
        date_prefix = mod_time.strftime("%Y-%m-%d")

        # Skip files that are already renamed (start with date pattern) unless forced
        import re

        if not force_rename and re.match(r"^\d{4}-\d{2}-\d{2} - ", file_path.name):
            logger.info(f"File already renamed: {file_path.name}")
            return

        # Get file description
        description = get_file_description(file_path, separator)

        # Create new filename with smart truncation for the full name
        extension = file_path.suffix
        base_new_name = f"{date_prefix} - {description}{extension}"

        # Apply smart truncation to the entire filename if needed
        if len(base_new_name) > 200:  # Conservative limit for cross-platform compatibility
            # Calculate space available for description
            prefix_and_suffix_length = len(f"{date_prefix} - {extension}")
            available_for_description = 200 - prefix_and_suffix_length
            truncated_description = _smart_truncate(description, available_for_description)
            base_new_name = f"{date_prefix} - {truncated_description}{extension}"

        # Handle filename collisions
        used_names = set()  # Empty set for single file
        new_name = _resolve_filename_collision(base_new_name, used_names, file_path.parent)

        new_path = file_path.parent / new_name

        if dry_run:
            logger.info(f"Would rename: {file_path.name} -> {new_name}")
        else:
            file_path.rename(new_path)
            logger.info(f"Renamed: {file_path.name} -> {new_name}")
    except Exception as e:
        logger.error(f"Error processing {file_path.name}: {str(e)}")


def rename_files(
    directory: Path | str,
    dry_run: bool = False,
    separator: str = "dash",
    include_hidden: bool = False,
    force_rename: bool = False,
) -> None:
    """Rename files in the directory based on their modification date and contents.

    ### Args:
        directory: Path to the directory containing files to rename.
        dry_run: If True, only show what would be renamed without making changes.
        separator: Preferred separator style ("dash" or "underscore").
        include_hidden: If True, include hidden files (dot files) in processing.
        force_rename: If True, re-process files that are already renamed.

    ### Example:
        ```python
        # Preview changes, skipping hidden files and already renamed files
        rename_files("~/Documents", dry_run=True)

        # Force re-processing of already renamed files
        rename_files("~/Documents", force_rename=True)
        ```
    """
    directory = Path(directory)
    if not directory.exists():
        logger.error(f"Directory {directory} does not exist")
        return

    # Track used filenames to prevent collisions
    used_names = set()

    for file_path in directory.iterdir():
        if file_path.is_file():
            # Skip hidden files (dot files) unless explicitly included
            if not include_hidden and file_path.name.startswith("."):
                logger.debug(f"Skipping hidden file: {file_path.name}")
                continue

            try:
                # Get modification time
                mod_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                date_prefix = mod_time.strftime("%Y-%m-%d")

                # Skip files that are already renamed (start with date pattern) unless forced
                import re

                if not force_rename and re.match(r"^\d{4}-\d{2}-\d{2} - ", file_path.name):
                    logger.debug(f"Skipping already renamed file: {file_path.name}")
                    continue

                # Get file description
                description = get_file_description(file_path, separator)

                # Create new filename with smart truncation for the full name
                extension = file_path.suffix
                base_new_name = f"{date_prefix} - {description}{extension}"

                # Apply smart truncation to the entire filename if needed
                if len(base_new_name) > 200:  # Conservative limit for cross-platform compatibility
                    # Calculate space available for description
                    prefix_and_suffix_length = len(f"{date_prefix} - {extension}")
                    available_for_description = 200 - prefix_and_suffix_length
                    truncated_description = _smart_truncate(description, available_for_description)
                    base_new_name = f"{date_prefix} - {truncated_description}{extension}"

                # Handle filename collisions
                new_name = _resolve_filename_collision(base_new_name, used_names, file_path.parent)
                used_names.add(new_name)

                new_path = file_path.parent / new_name

                if dry_run:
                    logger.info(f"Would rename: {file_path.name} -> {new_name}")
                else:
                    file_path.rename(new_path)
                    logger.info(f"Renamed: {file_path.name} -> {new_name}")
            except Exception as e:
                logger.error(f"Error processing {file_path.name}: {str(e)}")


def _resolve_filename_collision(base_name: str, used_names: set, directory: Path) -> str:
    """Resolve filename collisions by adding a counter suffix.

    ### Args:
        base_name: The desired filename.
        used_names: Set of already used filenames in this session.
        directory: Directory where the file will be placed.

    ### Returns:
        A unique filename that doesn't conflict with existing or used names.
    """
    # Check if base name is already taken (either in used_names or exists on disk)
    if base_name not in used_names and not (directory / base_name).exists():
        return base_name

    # Split filename into name and extension
    if "." in base_name:
        name_part, extension = base_name.rsplit(".", 1)
        extension = f".{extension}"
    else:
        name_part = base_name
        extension = ""

    # Try adding counter suffixes until we find a unique name
    counter = 2
    while True:
        candidate_name = f"{name_part}-{counter}{extension}"

        # Check both our used_names set and actual filesystem
        if candidate_name not in used_names and not (directory / candidate_name).exists():
            return candidate_name

        counter += 1

        # Safety valve to prevent infinite loop
        if counter > 1000:
            import uuid

            unique_id = str(uuid.uuid4())[:8]
            return f"{name_part}-{unique_id}{extension}"


@click.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("--dry-run", is_flag=True, help="Show what would be renamed without making changes")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.option(
    "--separator",
    default="dash",
    type=click.Choice(["dash", "underscore"]),
    help="Preferred separator for filenames (default: dash)",
)
@click.option("--include-hidden", is_flag=True, help="Include hidden files (dot files) in processing")
@click.option("--force-rename", is_flag=True, help="Re-process files that are already renamed")
def main(path: str, dry_run: bool, verbose: bool, separator: str, include_hidden: bool, force_rename: bool) -> NoReturn:
    """Rename files or a single file in PATH based on their modification date and contents.

    ### Args:
        path: Path to the directory or file to rename.
        dry_run: If True, only show what would be renamed without making changes.
        verbose: If True, enable verbose logging.
        separator: Preferred separator style for filenames.
        include_hidden: If True, include hidden files (dot files) in processing.
        force_rename: If True, re-process files that are already renamed.
    """
    if verbose:
        logger.setLevel(logging.DEBUG)

    path_obj = Path(path)

    if path_obj.is_file():
        logger.info(f"Processing file: {path}")
        rename_single_file(path, dry_run, separator, force_rename)
    elif path_obj.is_dir():
        logger.info(f"Processing directory: {path}")
        rename_files(path, dry_run, separator, include_hidden, force_rename)
    else:
        logger.error(f"Path {path} is neither a file nor a directory")


if __name__ == "__main__":
    main()
