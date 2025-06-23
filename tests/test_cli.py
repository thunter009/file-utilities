"""Tests for the CLI module."""

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import mock_open

import pytest

from file_renamer.cli import get_file_description, rename_files, _extract_pdf_description, _score_description, _choose_best_description, _is_meaningful_line, _clean_filename, _resolve_filename_collision

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
    description = get_file_description(sample_file, "dash")
    assert description == "This-is-a-test-file"


def test_get_file_description_unreadable(tmp_path: Path, mocker: "MockerFixture") -> None:
    """Test handling of unreadable files.

    ### Args:
        tmp_path: Pytest fixture providing a temporary directory path.
        mocker: Pytest fixture for mocking.
    """
    file_path = tmp_path / "unreadable.txt"
    mocker.patch("builtins.open", mock_open(read_data=""))
    mocker.patch("builtins.open", side_effect=IOError)

    description = get_file_description(file_path, "dash")
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
    rename_files(tmp_path, dry_run=True, separator="dash", include_hidden=False)
    assert file1.exists()
    assert file2.exists()
    assert "Would rename" in caplog.text

    # Test actual renaming
    rename_files(tmp_path, dry_run=False, separator="dash", include_hidden=False)
    assert not file1.exists()
    assert not file2.exists()
    assert (tmp_path / "2024-02-14 - First-test-file.txt").exists()
    assert (tmp_path / "2024-02-14 - Second-test-file.txt").exists()


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
    
    mocker.patch("file_renamer.cli.PdfReader", return_value=mock_reader)
    mocker.patch("builtins.open", mock_open())
    
    description = _extract_pdf_description(pdf_path, "dash")
    assert description == "Sample-PDF-Document"


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
    
    mocker.patch("file_renamer.cli.PdfReader", return_value=mock_reader)
    mocker.patch("builtins.open", mock_open())
    
    description = _extract_pdf_description(pdf_path, "dash")
    assert description == "First-line-of-PDF-content"


def test_get_file_description_pdf(tmp_path: Path, mocker: "MockerFixture") -> None:
    """Test PDF file description through main function.

    ### Args:
        tmp_path: Pytest fixture providing a temporary directory path.
        mocker: Pytest fixture for mocking.
    """
    pdf_path = tmp_path / "document.pdf"
    
    mocker.patch("file_renamer.cli._extract_pdf_description", return_value="PDF-Document-Title")
    
    description = get_file_description(pdf_path, "dash")
    assert description == "PDF-Document-Title"


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
    result = _choose_best_description("untitled", "Project Analysis Report", "dash")
    assert result == "Project-Analysis-Report"
    
    # Original already good
    result = _choose_best_description("Financial Summary 2024", "Chapter 1", "dash")
    assert result == "Financial-Summary-2024"
    
    # Similar quality, prefer content
    result = _choose_best_description("Meeting Notes", "Team Discussion Summary", "dash")
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
    
    description = get_file_description(md_file, "dash")
    assert description == "Project-Analysis-Report"


def test_get_file_description_preserves_good_filename(tmp_path: Path) -> None:
    """Test that good original filenames are preserved."""
    file_path = tmp_path / "Financial_Summary_2024.txt"
    file_path.write_text("import sys\n#comment\n1.")
    
    description = get_file_description(file_path, "dash")
    assert description == "Financial-Summary-2024"


def test_get_file_description_improves_bad_filename(tmp_path: Path) -> None:
    """Test that poor original filenames are improved with content."""
    file_path = tmp_path / "untitled.txt"
    file_path.write_text("# Annual Sales Report\n\nThis document contains the sales analysis.")
    
    description = get_file_description(file_path, "dash")
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
    
    description = get_file_description(file_path, "dash")
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


def test_hidden_files_skipped_by_default(tmp_path: Path, caplog: "LogCaptureFixture") -> None:
    """Test that hidden files are skipped by default."""
    # Create regular and hidden files
    regular_file = tmp_path / "document.txt"
    regular_file.write_text("Regular file content")
    
    hidden_file = tmp_path / ".hidden_file.txt"
    hidden_file.write_text("Hidden file content")
    
    dot_store = tmp_path / ".DS_Store"
    dot_store.write_text("System file content")
    
    # Test default behavior (should skip hidden files)
    rename_files(tmp_path, dry_run=True, separator="dash", include_hidden=False)
    
    # Should only process regular file
    assert "Would rename: document.txt" in caplog.text
    assert ".hidden_file.txt" not in caplog.text
    assert ".DS_Store" not in caplog.text


def test_hidden_files_included_when_requested(tmp_path: Path, caplog: "LogCaptureFixture") -> None:
    """Test that hidden files are included when explicitly requested."""
    # Create regular and hidden files
    regular_file = tmp_path / "document.txt"
    regular_file.write_text("Regular file content")
    
    hidden_file = tmp_path / ".hidden_file.txt"
    hidden_file.write_text("Hidden file content")
    
    # Test with include_hidden=True
    rename_files(tmp_path, dry_run=True, separator="dash", include_hidden=True)
    
    # Should process both files
    assert "Would rename: document.txt" in caplog.text
    assert "Would rename: .hidden_file.txt" in caplog.text


def test_resolve_filename_collision(tmp_path: Path) -> None:
    """Test filename collision resolution."""
    used_names = set()
    
    # Test no collision
    result = _resolve_filename_collision("document.txt", used_names, tmp_path)
    assert result == "document.txt"
    
    # Test collision with used names
    used_names.add("document.txt")
    result = _resolve_filename_collision("document.txt", used_names, tmp_path)
    assert result == "document-2.txt"
    
    # Test multiple collisions
    used_names.add("document-2.txt")
    result = _resolve_filename_collision("document.txt", used_names, tmp_path)
    assert result == "document-3.txt"
    
    # Test collision with existing file
    existing_file = tmp_path / "report.pdf"
    existing_file.write_text("existing content")
    
    result = _resolve_filename_collision("report.pdf", set(), tmp_path)
    assert result == "report-2.pdf"
    
    # Test file without extension
    result = _resolve_filename_collision("README", set(), tmp_path)
    assert result == "README"
    
    used_names_no_ext = {"README"}
    result = _resolve_filename_collision("README", used_names_no_ext, tmp_path)
    assert result == "README-2"


def test_filename_collision_handling_in_rename(tmp_path: Path, caplog: "LogCaptureFixture") -> None:
    """Test that rename_files handles filename collisions properly."""
    # Create two files with content that will generate the same description
    file1 = tmp_path / "document1.txt"
    file1.write_text("# Project Report\n\nFirst document")
    
    file2 = tmp_path / "document2.txt" 
    file2.write_text("# Project Report\n\nSecond document")
    
    # Both files should get processed without collision
    rename_files(tmp_path, dry_run=True, separator="dash", include_hidden=False)
    
    # Should see both files being renamed with collision resolution
    log_text = caplog.text
    assert "Would rename: document1.txt" in log_text
    assert "Would rename: document2.txt" in log_text
    
    # One should get the base name, the other should get a counter suffix
    assert "Project-Report.txt" in log_text
    assert "Project-Report-2.txt" in log_text


def test_collision_with_different_extensions(tmp_path: Path, caplog: "LogCaptureFixture") -> None:
    """Test collision handling with different file extensions."""
    # Create files that will have same base name but different extensions
    file1 = tmp_path / "doc.txt"
    file1.write_text("# Meeting Notes\n\nContent here")
    
    file2 = tmp_path / "doc.md"
    file2.write_text("# Meeting Notes\n\nSame content")
    
    rename_files(tmp_path, dry_run=True, separator="dash", include_hidden=False)
    
    log_text = caplog.text
    # Different extensions should not conflict
    assert "Meeting-Notes.txt" in log_text
    assert "Meeting-Notes.md" in log_text
    # Should not see any -2 suffixes since extensions are different
    assert "Meeting-Notes-2" not in log_text
