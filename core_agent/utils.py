import base64
import io
import os

import fitz
from PIL import Image


def save_uploaded_file(files, file_field_name='file', target_dir='.tmp'):
    """
    Saves an uploaded file from the request to the specified target directory.

    :param request: Django request object which contains FILES data.
    :param file_field_name: The key in request.FILES that holds the uploaded file.
    :param target_dir: Directory to which the file will be saved (default: '.tmp').
    :return: The path to the saved file.
    """
    # Create the target directory if it doesn't exist
    os.makedirs(target_dir, exist_ok=True)
    
    # Retrieve the file from the request
    uploaded_file = files[file_field_name]
    
    # Construct the path for saving the file
    file_path = os.path.join(target_dir, uploaded_file.name)
    
    # Write file to disk
    with open(file_path, 'wb+') as destination:
        for chunk in uploaded_file.chunks():
            destination.write(chunk)
    
    return file_path

def get_page_count(pdf_path: str):
    pdf_document = fitz.open(pdf_path)
    return pdf_document.page_count

def pdf_page_to_base64(pdf_path: str, page_number: int):
    pdf_document = fitz.open(pdf_path)
    # load the entire PDF for now
    page = pdf_document.load_page(page_number)
    # Render page to a pixmap
    pix = page.get_pixmap()
    # Convert pixmap to a PIL image
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    # Save as PNG into a bytes buffer
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    # Encode to base64
    image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return image_base64


def get_computed_system_prompt(prompt_template: str, metadata_fields: dict) -> str:
    """
    Computes a system prompt by replacing placeholders with values from metadata fields.
    
    Args:
        prompt_template (str): The template string containing placeholders in {FIELD_NAME} format
        metadata_fields (dict): Dictionary containing field names and their values
    
    Returns:
        str: The computed system prompt with all placeholders replaced
        
    Raises:
        KeyError: If a placeholder in the template doesn't have a corresponding value in metadata_fields
    """
    try:
        # Create a dictionary of uppercase keys for case-insensitive matching
        formatted_fields = {
            key.upper(): value 
            for key, value in metadata_fields.items()
        }
        
        # Replace each placeholder in the format {FIELD_NAME} with its corresponding value
        computed_prompt = prompt_template
        
        # Find all placeholders in the template using string formatting
        import re
        placeholders = re.findall(r'\{([^}]+)\}', prompt_template)
        
        # Replace each placeholder
        for placeholder in placeholders:
            key = placeholder.upper()
            if key not in formatted_fields:
                raise KeyError(f"Missing metadata field for placeholder: {placeholder}")
            
            computed_prompt = computed_prompt.replace(
                f"{{{placeholder}}}", 
                str(formatted_fields[key])
            )
            
        return computed_prompt
        
    except Exception as e:
        raise Exception(f"Error computing system prompt: {str(e)}")
