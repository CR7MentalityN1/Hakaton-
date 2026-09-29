"""Storage boundary: replace LocalStorage with an S3 implementation without changing API logic."""

from typing import Protocol
from pathlib import Path
from io import BytesIO
import uuid
import zipfile
from app.core.config import settings
from app.core.errors import fail


class FileStorage(Protocol):
    def save(self, content: bytes, extension: str) -> str: ...
    def path(self, key: str) -> Path: ...
    def delete(self, key: str) -> None: ...


class LocalStorage:
    def __init__(self):
        self.root = settings.data_dir / "uploads"
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, content, extension):
        key = uuid.uuid4().hex + "." + extension
        self.path(key).write_bytes(content)
        return key

    def path(self, key):
        path = (self.root / key).resolve()
        if path.parent != self.root.resolve():
            fail(400, "PATH_INVALID", "Недопустимое имя файла")
        return path

    def delete(self, key):
        self.path(key).unlink(missing_ok=True)


storage: FileStorage = LocalStorage()
FORMATS = {
    "png": ("image/png", b"\x89PNG\r\n\x1a\n"),
    "jpg": ("image/jpeg", b"\xff\xd8\xff"),
    "jpeg": ("image/jpeg", b"\xff\xd8\xff"),
    "pdf": ("application/pdf", b"%PDF-"),
    "zip": ("application/zip", b"PK"),
    "gzip": ("application/gzip", b"\x1f\x8b"),
    "gz": ("application/gzip", b"\x1f\x8b"),
    "rar": ("application/vnd.rar", b"Rar!"),
    "doc": ("application/msword", b"\xd0\xcf\x11\xe0"),
    "xls": ("application/vnd.ms-excel", b"\xd0\xcf\x11\xe0"),
    "docx": (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        b"PK",
    ),
    "xlsx": (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        b"PK",
    ),
}


def validate_file(content, filename, mime):
    ext = Path(filename).suffix.lower().lstrip(".")
    if len(content) > settings.upload_limit:
        fail(413, "UPLOAD_TOO_LARGE", f"Максимум {settings.max_upload_mb} МБ")
    if not content or ext not in FORMATS:
        fail(415, "FILE_TYPE_INVALID", "Формат файла не поддерживается")
    expected, signature = FORMATS[ext]
    aliases = {
        "application/octet-stream",
        "application/x-zip-compressed",
        "application/x-rar-compressed",
        "application/x-gzip",
        "application/x-rar",
    }
    if mime not in (expected, "") and mime not in aliases:
        fail(415, "MIME_INVALID", "MIME type не соответствует расширению")
    if not content.startswith(signature):
        fail(415, "FILE_CONTENT_INVALID", "Содержимое не соответствует расширению")
    if ext in ("docx", "xlsx"):
        try:
            with zipfile.ZipFile(BytesIO(content)) as z:
                if sum(i.file_size for i in z.infolist()) > 100 * 1024 * 1024:
                    fail(
                        413,
                        "ARCHIVE_TOO_LARGE",
                        "Распакованный документ превышает 100 МБ",
                    )
                if (
                    "xl/workbook.xml" if ext == "xlsx" else "word/document.xml"
                ) not in z.namelist():
                    raise ValueError()
        except (zipfile.BadZipFile, ValueError):
            fail(415, "FILE_CONTENT_INVALID", "Некорректный Office-файл")
    return ext, expected
