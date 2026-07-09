import base64
import io
import logging
import os
import re
import fitz
from PIL import Image
from django.utils.module_loading import import_string
from .settings import agent_settings
logger = logging.getLogger(__name__)


def save_uploaded_file(files, file_field_name='file', target_dir='.tmp'):
    os.makedirs(target_dir, exist_ok=True)
    uploaded_file = files[file_field_name]
    file_path = os.path.join(target_dir, uploaded_file.name)
    handler_path = agent_settings.UPLOAD_PREPROCESS_HANDLER
    if handler_path:
        preprocess = import_string(handler_path)
        content = preprocess(
            uploaded_file.read(),
            filename=uploaded_file.name,
            content_type=getattr(uploaded_file, 'content_type', None),
        )
        with open(file_path, 'wb') as destination:
            destination.write(content)
    else:
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


def base64_image_to_bytes(image_data: str) -> bytes:
    if image_data.startswith("data:"):
        image_data = image_data.split(",", 1)[1] if "," in image_data else ""
    return base64.b64decode(image_data)


def pages_base64_to_pdf(pages: list[str]) -> bytes:
    images = []
    for page in pages:
        if not page:
            continue
        image = Image.open(io.BytesIO(base64_image_to_bytes(page)))
        images.append(image.convert("RGB"))
    if not images:
        raise ValueError("No page images available to assemble into a PDF")
    buffer = io.BytesIO()
    images[0].save(buffer, format="PDF", save_all=True, append_images=images[1:])
    return buffer.getvalue()


def extract_placeholders_from_template(template: str) -> list:
    if not template:
        return []
    pattern = re.compile(r'\{([^}]+)\}')
    placeholders = pattern.findall(template)
    return list(set(placeholder.lower() for placeholder in placeholders))


def get_computed_system_prompt(prompt_template: str, metadata_fields: dict) -> str:
    try:
        fields_by_lower_key = {
            key.lower(): value
            for key, value in metadata_fields.items()
        }
        def _substitute(match: re.Match) -> str:
            name = match.group(1).lower()
            if name not in fields_by_lower_key:
                return match.group(0)
            return str(fields_by_lower_key[name])
        return re.sub(r'\{([^}]+)\}', _substitute, prompt_template)
    except Exception as e:
        raise Exception(f"Error computing system prompt: {str(e)}") from e
