import pdfplumber
import pytesseract
from PIL import Image
from typing import List, Optional
import re


def ocr_pdf(file_path: str, dpi: int = 300, lang: str = "eng") -> List[str]:
    """
    Perform OCR on each page of the provided PDF file and return a list of
    extracted text strings, one per page.

    - Uses pdfplumber to render pages to PIL images
    - Uses Tesseract OCR via pytesseract to extract text
    """
    texts: List[str] = []

    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            # Render page to image at the given DPI and convert to grayscale
            page_image = page.to_image(resolution=dpi).original.convert("L")
            # You can tweak PSM/OEM here if needed
            text = pytesseract.image_to_string(page_image, lang=lang)
            texts.append(text)

    return texts


def segment_questions(page_texts: List[str]) -> List[str]:
    """
    Naive question segmentation: tries to split text blocks whenever a line
    starts with patterns like "Q1", "Q 2.", "Question 3:" etc.
    This is a heuristic and will be replaced by a better approach later.
    """
    pattern = re.compile(r"(?:^|\n)\s*(?:Q\s*\d+\.?|Question\s*\d+\.?):?\s", re.IGNORECASE)

    combined = "\n".join(page_texts)
    # Ensure a leading marker to capture the first section
    combined = re.sub(r"^", "Q0: ", combined)

    splits = pattern.split(combined)
    # Remove the first synthetic split (for Q0)
    if splits and splits[0].strip().startswith("Q0:"):
        splits = splits[1:]

    # Clean up fragments
    segments = [s.strip() for s in splits if s.strip()]
    return segments
