"""Parser dispatch by extension/MIME. Supported: pdf, docx, txt, md, csv."""

from __future__ import annotations

from app.parsers.base import ParsedDocument
from app.parsers.csv_parser import parse_csv
from app.parsers.docx_parser import parse_docx
from app.parsers.pdf_parser import parse_pdf
from app.parsers.text_parsers import parse_markdown, parse_txt

SUPPORTED_EXTENSIONS = {"pdf", "docx", "txt", "md", "markdown", "csv"}

_MIME_TO_EXT = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "text/plain": "txt",
    "text/markdown": "md",
    "text/csv": "csv",
    "application/csv": "csv",
}


class UnsupportedFileType(Exception):
    pass


def resolve_extension(filename: str | None, mime: str | None) -> str:
    if filename and "." in filename:
        ext = filename.rsplit(".", 1)[1].lower()
        if ext in SUPPORTED_EXTENSIONS:
            return "md" if ext == "markdown" else ext
    if mime and mime in _MIME_TO_EXT:
        return _MIME_TO_EXT[mime]
    raise UnsupportedFileType(f"unsupported_file_type: filename={filename} mime={mime}")


def parse_file(data: bytes, *, filename: str | None, mime: str | None) -> ParsedDocument:
    ext = resolve_extension(filename, mime)
    if ext == "pdf":
        return parse_pdf(data, filename)
    if ext == "docx":
        return parse_docx(data, filename)
    if ext == "csv":
        return parse_csv(data, filename)
    if ext == "md":
        return parse_markdown(data, filename)
    return parse_txt(data, filename)


__all__ = [
    "ParsedDocument",
    "SUPPORTED_EXTENSIONS",
    "UnsupportedFileType",
    "parse_csv",
    "parse_file",
    "resolve_extension",
]
