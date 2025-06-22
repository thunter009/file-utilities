"""Tests for the CLI module."""

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import mock_open

import pytest

from file_renamer.cli import get_file_description, rename_files, _extract_pdf_description, _score_description, _choose_best_description, _is_meaningful_line, _clean_filename

if TYPE_CHECKING:
    from _pytest.logging import LogCaptureFixture
    from _pytest.monkeypatch import MonkeyPatch
    from pytest_mock.plugin import MockerFixture


@pytest.fixture
def sample_file(tmp_path: Path) -> Path:
    """Create a sample file for testing.

    ### Args:
        tmp_path: Pytest fixture providing a temporary directory path.

    ### Returns:
        Path to the created sample file.
    """
    file_path = tmp_path / "test.txt"
    file_path.write_text("This is a test file\nSecond line")
    return file_path


def test_get_file_description(sample_file: Path) -> None:
    """Test generating file description from contents.

    ### Args:
        sample_file: Fixture providing a sample file path.
    """
    description = get_file_description(sample_file)
    assert description == "This is a test file"


def test_get_file_description_unreadable(tmp_path: Path, mocker: "MockerFixture") -> None:
    """Test handling of unreadable files.

    ### Args:
        tmp_path: Pytest fixture providing a temporary directory path.
        mocker: Pytest fixture for mocking.
    """
    file_path = tmp_path / "unreadable.txt"
    mocker.patch("builtins.open", mock_open(read_data=""))
    mocker.patch("builtins.open", side_effect=IOError)

    description = get_file_description(file_path)
    assert description == "unreadable"


def test_rename_files(tmp_path: Path, monkeypatch: "MonkeyPatch", caplog: "LogCaptureFixture") -> None:
    """Test file renaming functionality.

    ### Args:
        tmp_path: Pytest fixture providing a temporary directory path.
        monkeypatch: Pytest fixture for monkeypatching.
        caplog: Pytest fixture for capturing log output.
    """
    # Create test files
    file1 = tmp_path / "test1.txt"
    file1.write_text("First test file")
    file2 = tmp_path / "test2.txt"
    file2.write_text("Second test file")

    # Mock datetime to return consistent timestamp
    from datetime import datetime

    mock_datetime = datetime(2024, 2, 14, 12, 0, 0)

    class MockDateTime:
        @staticmethod
        def fromtimestamp(_ts: float) -> datetime:
            return mock_datetime

    monkeypatch.setattr("file_renamer.cli.datetime", MockDateTime)

    # Ensure logger level is set to capture INFO messages
    import logging

    logging.getLogger("file_renamer.cli").setLevel(logging.INFO)

    # Test dry run
    rename_files(tmp_path, dry_run=True)
    assert file1.exists()
    assert file2.exists()
    assert "Would rename" in caplog.text

    # Test actual renaming
    rename_files(tmp_path, dry_run=False)
    assert not file1.exists()
    assert not file2.exists()
    assert (tmp_path / "2024-02-14 - First test file.txt").exists()
    assert (tmp_path / "2024-02-14 - Second test file.txt").exists()


def test_extract_pdf_description_with_title(tmp_path: Path, mocker: "MockerFixture") -> None:
    """Test PDF description extraction using metadata title.

    ### Args:
        tmp_path: Pytest fixture providing a temporary directory path.
        mocker: Pytest fixture for mocking.
    """
    pdf_path = tmp_path / "test.pdf"
    
    # Mock PyPDF2 components
    mock_metadata = mocker.MagicMock()
    mock_metadata.title = "Sample PDF Document"
    
    mock_reader = mocker.MagicMock()
    mock_reader.metadata = mock_metadata
    
    mocker.patch("file_renamer.cli.PyPDF2.PdfReader", return_value=mock_reader)
    mocker.patch("builtins.open", mock_open())
    
    description = _extract_pdf_description(pdf_path)
    assert description == "Sample PDF Document"


def test_extract_pdf_description_with_text(tmp_path: Path, mocker: "MockerFixture") -> None:
    """Test PDF description extraction from page text.

    ### Args:
        tmp_path: Pytest fixture providing a temporary directory path.
        mocker: Pytest fixture for mocking.
    """
    pdf_path = tmp_path / "test.pdf"
    
    # Mock PyPDF2 components
    mock_page = mocker.MagicMock()
    mock_page.extract_text.return_value = "First line of PDF content\nSecond line"
    
    mock_reader = mocker.MagicMock()
    mock_reader.metadata = None
    mock_reader.pages = [mock_page]
    
    mocker.patch("file_renamer.cli.PyPDF2.PdfReader", return_value=mock_reader)
    mocker.patch("builtins.open", mock_open())
    
    description = _extract_pdf_description(pdf_path)
    assert description == "First line of PDF content"


def test_get_file_description_pdf(tmp_path: Path, mocker: "MockerFixture") -> None:
    """Test PDF file description through main function.

    ### Args:
        tmp_path: Pytest fixture providing a temporary directory path.
        mocker: Pytest fixture for mocking.
    """
    pdf_path = tmp_path / "document.pdf"
    
    mocker.patch("file_renamer.cli._extract_pdf_description", return_value="PDF Document Title")
    
    description = get_file_description(pdf_path)
    assert description == "PDF Document Title"


def test_score_description() -> None:
    """Test description scoring logic."""
    # Good descriptions
    assert _score_description("Project Report Analysis") >= 7
    assert _score_description("Meeting Minutes Summary") >= 7
    
    # Poor descriptions
    assert _score_description("untitled") <= 3
    assert _score_description("Document1") <= 3
    assert _score_description("") == 0
    
    # Medium descriptions
    assert 3 <= _score_description("Notes") <= 6
    assert 4 <= _score_description("Chapter One") <= 8


def test_choose_best_description() -> None:
    """Test choosing between original and content-based descriptions."""
    # Content significantly better
    result = _choose_best_description("untitled", "Project Analysis Report")
    assert result == "Project-Analysis-Report"
    
    # Original already good
    result = _choose_best_description("Financial Summary 2024", "Chapter 1")
    assert result == "Financial-Summary-2024"
    
    # Similar quality, prefer content
    result = _choose_best_description("Meeting Notes", "Team Discussion Summary")
    assert result == "Team-Discussion-Summary"


def test_is_meaningful_line() -> None:
    """Test meaningful line detection."""
    # Meaningful lines
    assert _is_meaningful_line("Project Analysis Report")
    assert _is_meaningful_line("Meeting with Client Team")
    
    # Uninformative lines
    assert not _is_meaningful_line("import sys")
    assert not _is_meaningful_line("# This is a comment")
    assert not _is_meaningful_line("Chapter 1")
    assert not _is_meaningful_line("1.")
    
    # Edge cases
    assert not _is_meaningful_line("A")  # Too short
    # Too long
    assert not _is_meaningful_line("This is a very long line with many words that exceeds reasonable limits")


def test_get_file_description_markdown_header(tmp_path: Path) -> None:
    """Test extracting description from markdown files with headers."""
    md_file = tmp_path / "document.md"
    md_file.write_text("# Project Analysis Report\n\nThis is the content of the document.")
    
    description = get_file_description(md_file)
    assert description == "Project-Analysis-Report"


def test_get_file_description_preserves_good_filename(tmp_path: Path) -> None:
    """Test that good original filenames are preserved."""
    file_path = tmp_path / "Financial_Summary_2024.txt"
    file_path.write_text("import sys\n#comment\n1.")
    
    description = get_file_description(file_path)
    assert description == "Financial-Summary-2024"


def test_get_file_description_improves_bad_filename(tmp_path: Path) -> None:
    """Test that poor original filenames are improved with content."""
    file_path = tmp_path / "untitled.txt"
    file_path.write_text("# Annual Sales Report\n\nThis document contains the sales analysis.")
    
    description = get_file_description(file_path)
    assert description == "Annual-Sales-Report"


def test_clean_filename() -> None:
    """Test filename cleaning with different separators."""
    # Test dash separator (default)
    assert _clean_filename("Project Report Analysis") == "Project-Report-Analysis"
    assert _clean_filename("File_with_underscores") == "File-with-underscores"
    assert _clean_filename("Special@#$Characters") == "Special-Characters"
    
    # Test underscore separator
    assert _clean_filename("Project Report Analysis", "underscore") == "Project_Report_Analysis"
    assert _clean_filename("File-with-dashes", "underscore") == "File_with_dashes"
    
    # Test consecutive separators
    assert _clean_filename("Multiple   Spaces", "dash") == "Multiple-Spaces"
    assert _clean_filename("Multiple___Underscores", "underscore") == "Multiple_Underscores"


def test_all_caps_conversion(tmp_path: Path) -> None:
    """Test that ALL CAPS titles are converted to Capital Case."""
    file_path = tmp_path / "document.txt"
    file_path.write_text("PROJECT ANALYSIS REPORT\n\nThis is the content.")
    
    description = get_file_description(file_path)
    assert description == "Project-Analysis-Report"


def test_separator_preference(tmp_path: Path) -> None:
    """Test that separator preference is respected."""
    file_path = tmp_path / "document.txt"
    file_path.write_text("# Project Analysis Report\n\nContent here.")
    
    # Test dash separator
    description_dash = get_file_description(file_path, "dash")
    assert description_dash == "Project-Analysis-Report"
    
    # Test underscore separator
    description_underscore = get_file_description(file_path, "underscore")
    assert description_underscore == "Project_Analysis_Report"
