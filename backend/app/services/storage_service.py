from pathlib import Path
from uuid import UUID, uuid4

from fastapi import UploadFile

from app.core.config import get_settings


class LocalStorageService:
    """Local MVP storage behind a narrow interface that can later be replaced by object storage."""

    def __init__(self, root: Path | None = None, max_size: int | None = None) -> None:
        settings = get_settings()
        self.root = (root or settings.storage_root).resolve()
        self.max_size = max_size or settings.max_upload_size_bytes

    def save_upload(self, upload: UploadFile, *, exam_id: UUID, student_id: UUID | None, extension: str) -> tuple[str, str, int]:
        return self._save(upload, relative_directory=Path("answer-sheets") / str(exam_id) / (str(student_id) if student_id else "unassigned"), extension=extension)

    def save_question_paper(self, upload: UploadFile, *, exam_id: UUID, extension: str) -> tuple[str, str, int]:
        return self._save(upload, relative_directory=Path("question-papers") / str(exam_id), extension=extension)

    def _save(self, upload: UploadFile, *, relative_directory: Path, extension: str) -> tuple[str, str, int]:
        stored_filename = f"{uuid4().hex}{extension}"
        relative_path = relative_directory / stored_filename
        destination = (self.root / relative_path).resolve()
        if self.root not in destination.parents:
            raise ValueError("Invalid storage path")
        destination.parent.mkdir(parents=True, exist_ok=True)
        total = 0
        try:
            with destination.open("xb") as output:
                while chunk := upload.file.read(1024 * 1024):
                    total += len(chunk)
                    if total > self.max_size:
                        raise ValueError(f"File exceeds the maximum allowed size of {self.max_size} bytes")
                    output.write(chunk)
        except Exception:
            destination.unlink(missing_ok=True)
            raise
        return stored_filename, str(relative_path), total

    def delete(self, relative_path: str) -> None:
        destination = (self.root / relative_path).resolve()
        if self.root not in destination.parents:
            return
        destination.unlink(missing_ok=True)

    def save_generated(self, content: bytes, *, relative_path: Path) -> str:
        """Store generated page images without exposing a caller-controlled path."""
        destination = (self.root / relative_path).resolve()
        if self.root not in destination.parents:
            raise ValueError("Invalid storage path")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
        return str(relative_path)

    def absolute_path(self, relative_path: str) -> Path:
        destination = (self.root / relative_path).resolve()
        if self.root not in destination.parents:
            raise ValueError("Invalid storage path")
        return destination
