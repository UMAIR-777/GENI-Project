from typing import Optional
from PyPDF2 import PdfReader, PdfWriter
from PyPDF2.generic import NameObject, TextStringObject
from langchain_groq import ChatGroq
import os


# Set up Groq API
os.environ['GROQ_API_KEY'] = 'your_groq_api_key'  # Replace with your actual API key
llm = ChatGroq(temperature=0.7, model="llama-3.3-70b-versatile")


def ai_fill_pdf_groq(
    context: str,
    pdf_file: str,
    specify_pages: Optional[list] = None,
    temperature: float = 0.7
) -> str:
    """
    Fills a PDF form using Groq AI to generate values for the fields.

    Args:
        context (str): Information or instructions for filling the form.
        pdf_file (str): Path to the fillable PDF file.
        specify_pages (list, optional): Pages to fill. Fills all pages if None.
        temperature (float): Controls the creativity of the AI model's output (0-1).

    Returns:
        str: Path to the filled PDF file.
    """
    try:
        # Load the fillable PDF
        reader = PdfReader(pdf_file)
        writer = PdfWriter()

        # Extract fillable fields from the PDF
        fields = {}
        for page in reader.pages:
            if "/Annots" in page:
                for annot in page["/Annots"]:
                    field = annot.get_object()
                    if "/T" in field and "/V" in field:
                        field_name = field["/T"]
                        fields[field_name] = ""

        # Generate responses for each field using Groq AI
        filled_fields = {}
        for field_name in fields:
            # Generate Groq message
            messages = [
                (
                    "system",
                    f"""
                    You are an assistant that fills out forms using context and field names. 
                    Your task is to provide accurate and professional responses for the given field.
                    """
                ),
                (
                    "human",
                    f"""
                    Based on the context:
                    {context}

                    Provide a value for the field '{field_name}'.
                    """
                ),
            ]
            response = llm.invoke(messages)
            filled_fields[field_name] = response.content.strip() if response else ""

        # Fill the fields in the PDF
        for page_number, page in enumerate(reader.pages):
            if specify_pages and (page_number + 1) not in specify_pages:
                writer.add_page(page)
                continue

            if "/Annots" in page:
                for annot in page["/Annots"]:
                    field = annot.get_object()
                    if "/T" in field and field["/T"] in filled_fields:
                        field.update({
                            NameObject("/V"): TextStringObject(filled_fields[field["/T"]])
                        })
            writer.add_page(page)

        # Save the filled PDF
        filled_pdf_path = pdf_file.replace(".pdf", "_filled.pdf")
        with open(filled_pdf_path, "wb") as filled_pdf:
            writer.write(filled_pdf)

        return filled_pdf_path

    except Exception as e:
        raise ValueError(f"Error in AI Fill PDF with Groq: {e}")
