from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import fitz
from PIL import Image, ImageOps, UnidentifiedImageError


class DocumentProcessingError(ValueError): pass

@dataclass(frozen=True)
class DocumentExtraction:
    text: str
    images: list[bytes]
    use_text: bool

class QuestionPaperDocumentService:
    def extract(self, path: Path, mime_type: str) -> DocumentExtraction:
        return self._extract_pdf(path) if mime_type == "application/pdf" else DocumentExtraction("", [self._image(path)], False)
    def _extract_pdf(self, path: Path) -> DocumentExtraction:
        try:
            document = fitz.open(path)
            if document.page_count == 0: raise DocumentProcessingError("The PDF has no pages")
            text = "\n\n".join(page.get_text("text").strip() for page in document).strip()
            # Short but complete digitally-generated papers should still avoid vision.
            if len(text) >= 40: return DocumentExtraction(text, [], True)
            # 144 DPI retains right-aligned and small printed marks while staying practical for local vision models.
            return DocumentExtraction(text, [page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False).tobytes("png") for page in document], False)
        except DocumentProcessingError: raise
        except Exception as error: raise DocumentProcessingError("Unable to read the PDF") from error
    def _image(self, path: Path) -> bytes:
        try:
            with Image.open(path) as image:
                image = ImageOps.exif_transpose(image).convert("RGB"); image.thumbnail((2048, 2048))
                output = BytesIO(); image.save(output, format="PNG", optimize=True); return output.getvalue()
        except (UnidentifiedImageError, OSError) as error: raise DocumentProcessingError("Unable to read the uploaded image") from error
