"""등기부등본 파일(PDF/이미지)에서 텍스트를 추출한다.

PDF는 pypdf로 임베디드 텍스트 레이어를 직접 읽는다 (인터넷등기소 전자발급 등기부등본은
대부분 텍스트 PDF). 이미지(PNG/JPG)는 pytesseract OCR을 시도하되, OCR 엔진(Tesseract)이
서버에 설치되어 있지 않으면 설치 안내와 함께 실패를 알린다 — 프로토타입 단계의 제약사항이며,
스캔본 PDF도 같은 이유로 현재는 지원하지 않는다.
"""

import io

import pypdf
from PIL import Image

MIN_TEXT_LENGTH = 30


class RegistryExtractionError(Exception):
    pass


def extract_text(filename: str, content: bytes) -> tuple[str, str]:
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""

    if ext == "pdf":
        return _extract_pdf_text(content), "pdf"
    if ext in ("png", "jpg", "jpeg"):
        return _extract_image_text(content), "image"

    raise RegistryExtractionError(f"지원하지 않는 파일 형식입니다 (.{ext}). PDF 또는 PNG/JPG 파일을 업로드해주세요.")


def _extract_pdf_text(content: bytes) -> str:
    try:
        reader = pypdf.PdfReader(io.BytesIO(content))
        pages_text = [page.extract_text() or "" for page in reader.pages]
    except Exception as e:
        raise RegistryExtractionError(f"PDF 파일을 읽을 수 없습니다: {e}") from e

    text = "\n".join(pages_text).strip()
    if len(text) < MIN_TEXT_LENGTH:
        raise RegistryExtractionError(
            "PDF에서 텍스트를 추출하지 못했습니다. 스캔본(이미지) PDF는 현재 지원되지 않습니다. "
            "인터넷등기소에서 발급한 전자문서(텍스트 PDF)를 업로드해주세요."
        )
    return text


def _extract_image_text(content: bytes) -> str:
    import pytesseract

    try:
        image = Image.open(io.BytesIO(content))
    except Exception as e:
        raise RegistryExtractionError(f"이미지 파일을 읽을 수 없습니다: {e}") from e

    try:
        text = pytesseract.image_to_string(image, lang="kor+eng")
    except pytesseract.TesseractNotFoundError as e:
        raise RegistryExtractionError(
            "서버에 OCR 엔진(Tesseract)이 설치되어 있지 않아 이미지 인식을 수행할 수 없습니다. "
            "PDF 형식의 등기부등본을 업로드해주세요."
        ) from e
    except Exception as e:
        raise RegistryExtractionError(f"이미지 OCR 처리 중 오류가 발생했습니다: {e}") from e

    text = text.strip()
    if len(text) < MIN_TEXT_LENGTH:
        raise RegistryExtractionError("이미지에서 텍스트를 충분히 인식하지 못했습니다. 더 선명한 이미지로 다시 시도해주세요.")
    return text
