import base64
import io
import os
import re
import fitz
from PIL import Image


def save_uploaded_file(files, file_field_name='file', target_dir='.tmp'):
    os.makedirs(target_dir, exist_ok=True)
    uploaded_file = files[file_field_name]
    file_path = os.path.join(target_dir, uploaded_file.name)
    with open(file_path, 'wb+') as destination:
        for chunk in uploaded_file.chunks():
            destination.write(chunk)
    return file_path


def get_page_count(pdf_path: str):
    pdf_document = fitz.open(pdf_path)
    return pdf_document.page_count


def pdf_page_to_base64(pdf_path: str, page_number: int) -> tuple[str, str]:
    pdf_document = fitz.open(pdf_path)
    page = pdf_document.load_page(page_number)
    pix = page.get_pixmap()
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return image_base64, "image/png"


def extract_placeholders_from_template(template: str) -> list:
    if not template:
        return []
    pattern = re.compile(r'\{([^}]+)\}')
    placeholders = pattern.findall(template)
    return list(set(placeholder.lower() for placeholder in placeholders))


def get_computed_system_prompt(prompt_template: str, metadata_fields: dict) -> str:
    try:
        formatted_fields = {
            key.lower(): value
            for key, value in metadata_fields.items()
        }
        computed_prompt = prompt_template
        for field_key_lower, field_value in formatted_fields.items():
            pattern = re.compile(r'\{' + re.escape(field_key_lower) + r'\}', re.IGNORECASE)
            computed_prompt = pattern.sub(str(field_value), computed_prompt)
        return computed_prompt
    except Exception as e:
        raise Exception(f"Error computing system prompt: {str(e)}")
