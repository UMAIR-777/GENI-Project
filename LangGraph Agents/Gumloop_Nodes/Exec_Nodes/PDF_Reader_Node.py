from PyPDF2 import PdfReader
import requests
from io import BytesIO

def pdf_reader(file_name=None, use_link=None, specify_pages=None, split_by_page=False):
    """
    Reads content from a PDF file or URL.

    Args:
        file_name (str): Path to the PDF file or URL if `use_link` is enabled.
        use_link (bool): If True, reads PDF from the provided URL.
        specify_pages (list): List of page numbers to read (1-indexed).
        split_by_page (bool): If True, splits content by page and returns as a list.

    Returns:
        str or list: Extracted PDF content. Returns a string if `split_by_page` is False; otherwise, returns a list of strings.
    """
    try:
        # Read PDF from URL or local file
        if use_link:
            response = requests.get(file_name)
            response.raise_for_status()
            pdf = PdfReader(BytesIO(response.content))
        else:
            pdf = PdfReader(file_name)

        # Determine which pages to read
        pages = specify_pages if specify_pages else range(len(pdf.pages))

        # Extract content
        content = []
        for page in pages:
            content.append(pdf.pages[page - 1].extract_text())

        # Return content as a single string or split by page
        return content if split_by_page else "\n".join(content)
    except Exception as e:
        raise ValueError(f"Error reading PDF: {e}")
