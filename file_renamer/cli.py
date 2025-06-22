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
import PyPDF2

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
        if file_path.suffix.lower() == '.pdf':
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
    
    lines = [line.strip() for line in content.split('\n') if line.strip()]
    
    if not lines:
        return os.path.splitext(file_path.name)[0]
    
    # Try to find the most descriptive line
    candidates = []
    
    # Look for title-like patterns (markdown headers, etc.)
    for line in lines[:10]:  # Check first 10 lines
        if line.startswith('#'):
            # Markdown header
            candidates.append((line.lstrip('#').strip(), 10))
        elif line.isupper() and len(line.split()) <= 6:
            # ALL CAPS title - convert to Capital Case
            title_case = line.title()
            candidates.append((title_case, 8))
        elif line.endswith(':') and len(line.split()) <= 4:
            # Section header ending with colon
            candidates.append((line.rstrip(':'), 6))
    
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
    return _clean_filename(best_text, separator)[:50]


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
        r'^import\s+',
        r'^from\s+.*import',
        r'^#.*',
        r'^//.*',
        r'^/\*.*',
        r'^\s*$',
        # Common document patterns
        r'^chapter\s+\d+$',
        r'^section\s+\d+$',
        r'^page\s+\d+$',
        r'^\d+\.$',  # Just numbers
        r'^[IVXivx]+\.$',  # Roman numerals
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
    
    logger.debug(f"Original '{cleaned_original}' score: {original_score}, "
                f"Content '{cleaned_content}' score: {content_score}")
    
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
        description: The description to score.

    ### Returns:
        Score from 0-10, higher is better.
    """
    if not description:
        return 0
    
    score = 0
    words = description.split()
    
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
    generic_patterns = ['untitled', 'document', 'file', 'new', 'copy', 'temp', 'test']
    if any(pattern in description.lower() for pattern in generic_patterns):
        score -= 2
    
    # Bonus for descriptive words
    descriptive_words = ['report', 'analysis', 'summary', 'guide', 'manual', 'proposal', 'plan']
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
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            
            # Try to get title from metadata first
            if reader.metadata and reader.metadata.title:
                title = reader.metadata.title.strip()
                if title:
                    # Convert ALL CAPS to title case
                    if title.isupper():
                        title = title.title()
                    return _clean_filename(title, separator)[:50]
            
            # Fall back to extracting text from first page
            if len(reader.pages) > 0:
                first_page = reader.pages[0]
                text = first_page.extract_text()
                
                # Get first meaningful line of text
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                if lines:
                    first_line = lines[0]
                    # Convert ALL CAPS to title case
                    if first_line.isupper():
                        first_line = first_line.title()
                    return _clean_filename(first_line, separator)[:50]
                    
    except Exception as e:
        logger.warning(f"Could not extract PDF content from {file_path}: {str(e)}")
    
    # Return filename without extension as fallback
    return os.path.splitext(file_path.name)[0]


def rename_files(directory: Path | str, dry_run: bool = False, separator: str = "dash") -> None:
    """Rename files in the directory based on their modification date and contents.

    ### Args:
        directory: Path to the directory containing files to rename.
        dry_run: If True, only show what would be renamed without making changes.
        separator: Preferred separator style ("dash" or "underscore").

    ### Example:
        ```python
        # Preview changes
        rename_files("~/Documents", dry_run=True)

        # Apply changes with dash separators
        rename_files("~/Documents", separator="dash")
        ```
    """
    directory = Path(directory)
    if not directory.exists():
        logger.error(f"Directory {directory} does not exist")
        return

    for file_path in directory.iterdir():
        if file_path.is_file():
            try:
                # Get modification time
                mod_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                date_prefix = mod_time.strftime("%Y-%m-%d")

                # Get file description
                description = get_file_description(file_path, separator)

                # Create new filename
                extension = file_path.suffix
                new_name = f"{date_prefix} - {description}{extension}"
                new_path = file_path.parent / new_name

                if dry_run:
                    logger.info(f"Would rename: {file_path.name} -> {new_name}")
                else:
                    file_path.rename(new_path)
                    logger.info(f"Renamed: {file_path.name} -> {new_name}")
            except Exception as e:
                logger.error(f"Error processing {file_path.name}: {str(e)}")


@click.command()
@click.argument("directory", type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option("--dry-run", is_flag=True, help="Show what would be renamed without making changes")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.option("--separator", default="dash", type=click.Choice(["dash", "underscore"]), 
              help="Preferred separator for filenames (default: dash)")
def main(directory: str, dry_run: bool, verbose: bool, separator: str) -> NoReturn:
    """Rename files in DIRECTORY based on their modification date and contents.

    ### Args:
        directory: Path to the directory containing files to rename.
        dry_run: If True, only show what would be renamed without making changes.
        verbose: If True, enable verbose logging.
        separator: Preferred separator style for filenames.
    """
    if verbose:
        logger.setLevel(logging.DEBUG)

    logger.info(f"Processing directory: {directory}")
    rename_files(directory, dry_run, separator)


if __name__ == "__main__":
    main()
