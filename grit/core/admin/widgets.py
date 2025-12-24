import uuid
import json
from django import forms
from django.utils.html import format_html


def render_upload_button(fetch_url=None, button_label="Upload File", file_field_name='file'):
    """
    Renders a file upload button with JavaScript to handle the upload.
    :param fetch_url: URL to send the file to.
    :param button_label: Label for the upload button.
    :return: HTML string for the upload button.
    
    formData is file_upload
    """
    if fetch_url is None or fetch_url == "":
        raise ValueError("fetch_url must be provided")
    element_id = uuid.uuid4()
    return format_html(
        """
        <div class="upload-form">
            <input type="file" id="file-upload_{element_id}" name="file" />
            <button id="upload-button_{element_id}" data-element-id="{element_id}">{button_label}</button>
            <div id="upload-status_{element_id}" style="display:none;"></div>
        </div>
        <script>
        document.addEventListener("DOMContentLoaded", function() {{
            function getCookie(name) {{
                let cookieValue = null;
                if (document.cookie && document.cookie !== '') {{
                    const cookies = document.cookie.split(';');
                    for (let i = 0; i < cookies.length; i++) {{
                        const cookie = cookies[i].trim();
                        // Check if this cookie string begins with the name we want.
                        if (cookie.substring(0, name.length + 1) === (name + '=')) {{
                            cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                            break;
                        }}
                    }}
                }}
                return cookieValue;
            }}

            const uploadButton = document.querySelector("#upload-button_{element_id}");
            const statusDiv = document.querySelector("#upload-status_{element_id}");

            uploadButton.addEventListener("click", function(event) {{
                event.preventDefault();
                const elementId = event.target.dataset.elementId;
                const fileInput = document.getElementById('file-upload_' + elementId);
                if (!fileInput.files.length) {{
                    alert('Please select a file first');
                    return;
                }}

                // Show loading indicator
                uploadButton.disabled = true;
                statusDiv.textContent = 'Uploading...';
                statusDiv.style.display = 'block';
                statusDiv.style.color = 'blue';

                const csrfToken = getCookie('csrftoken');
                
                const formData = new FormData();
                formData.append('{file_field_name}', fileInput.files[0]);
                formData.append('csrfmiddlewaretoken', csrfToken);
                
                fetch("{fetch_url}", {{
                    method: 'POST',
                    body: formData,
                    credentials: 'same-origin'
                }})
                .then(response => {{
                    if (!response.ok) {{
                        return response.text().then(text => {{
                            throw new Error(text || 'Upload failed');
                        }});
                    }}
                    return response.json();
                }})
                .then(data => {{
                    statusDiv.textContent = data.message || 'Upload successful';
                    statusDiv.style.color = 'green';
                    statusDiv.style.display = 'block';
                    
                    if (data.redirect_url) {{
                        window.location.href = data.redirect_url;
                    }} else {{
                        setTimeout(() => {{
                            window.location.reload();
                        }}, 1500);
                    }}
                }})
                .catch(error => {{
                    console.error('Error:', error);
                    uploadButton.disabled = false;
                    statusDiv.textContent = error.message || 'Upload error';
                    statusDiv.style.color = 'red';
                    statusDiv.style.display = 'block';
                }});
            }});
        }});
        </script>
    """,
        fetch_url=fetch_url,
        element_id=element_id,
        button_label=button_label,
        file_field_name=file_field_name,
    )


def render_tags_view(tags: dict) -> str:
    """
    Renders a list of tags as HTML.
    :param tags: List of tags to render.
    :return: HTML string for the tags.
    """
    if tags is None or not isinstance(tags, dict):
        return ""
    tag_html = ''.join(f'<div>{key}: {value}</div>' for key, value in tags.items())
    return format_html(tag_html)


class DictWidget(forms.Widget):
    template_name = 'core/dict_widget.html'

    def __init__(self, attrs=None, add_button_label="Add", remove_button_label="Remove"):
        # You can pass in additional attributes or default values here
        super().__init__(attrs)
        self.add_button_label = add_button_label
        self.remove_button_label = remove_button_label

    def get_context(self, name, value, attrs):
        """
        Build the context passed to the template. 
        'value' should typically be a JSON string or a Python dict of key-value pairs.
        """
        context = super().get_context(name, value, attrs)
        if not value:
            # If empty, default to an empty dict
            value = {}
        elif isinstance(value, str):
            # If it's a JSON string, try to parse it
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                value = {}

        # Convert dict into a list of (key, value) pairs for easier template iteration
        if isinstance(value, dict):
            kv_list = list(value.items())
        else:
            kv_list = []

        context['widget']['name'] = name
        context['widget']['value'] = json.dumps(value)  # store original as JSON
        context['widget']['kv_list'] = kv_list          # to display in table
        context['widget']['add_button_label'] = self.add_button_label
        context['widget']['remove_button_label'] = self.remove_button_label
        context['widget']['attrs'].update(attrs or {})
        return context

    def format_value(self, value):
        """
        How the widget’s value is displayed as an HTML string.
        Usually we rely on the template for display, so this can be empty or just return JSON.
        """
        if value is None:
            return ''
        if isinstance(value, dict):
            return json.dumps(value)
        return value

    def value_from_datadict(self, data, files, name):
        """
        Once the form is submitted, Django passes the POST data here.
        We expect the JSON from our hidden field (e.g., <input type="hidden">).
        """
        raw_value = data.get(name, '')
        try:
            parsed = json.loads(raw_value)
            if not isinstance(parsed, dict):
                return {}
            return parsed
        except json.JSONDecodeError:
            return {}


class ListWidget(forms.Widget):
    template_name = 'core/list_widget.html'

    def __init__(self, attrs=None, add_button_label="Add", remove_button_label="Remove"):
        super().__init__(attrs)
        self.add_button_label = add_button_label
        self.remove_button_label = remove_button_label

    def get_context(self, name, value, attrs):
        """
        Build the context passed to the template.
        'value' is expected to be a list of strings or a single string (which we split).
        """
        context = super().get_context(name, value, attrs)

        # Convert empty values to an empty list
        if not value:
            value = []
        # If it's already a string (e.g., initial data), split by comma
        elif isinstance(value, str):
            value = [v.strip() for v in value.split(',') if v.strip()]

        # The field's "value" will be displayed as a comma-separated string
        context['widget']['value'] = ', '.join(value)

        # If your template needs iteration over the items:
        context['widget']['list_items'] = value

        # Pass the custom labels into the template
        context['widget']['add_button_label'] = self.add_button_label
        context['widget']['remove_button_label'] = self.remove_button_label

        # Make sure any custom attributes are placed on the widget
        context['widget']['attrs'].update(attrs or {})
        return context

    def format_value(self, value):
        """
        How the widget's value is displayed as a string.
        Here, we'll join the list into a comma-separated string.
        """
        if not value:
            return ''
        if isinstance(value, list):
            return ','.join(value)
        return str(value)

    def value_from_datadict(self, data, files, name):
        """
        Extract the list of strings from the submitted POST data.
        We'll assume each input with the same name is a distinct item.
        """
        raw_values = data.getlist(name)  # Use getlist instead of get
        # If nothing was submitted, return an empty list
        if not raw_values:
            return []
        
        # Clean/strip each item. If your inputs might contain commas that you want
        # to further split, you could parse them here as well. 
        # But if you consider each input its own item, just strip and store:
        return [v.strip() for v in raw_values if v.strip()]


class ListListWidget(forms.Widget):
    """
    A custom widget that handles a list of list.
    """
    template_name = 'core/list_list_widget.html'

    def __init__(self, attrs=None, add_button_label="Add", remove_button_label="Remove"):
        super().__init__(attrs)
        self.add_button_label = add_button_label
        self.remove_button_label = remove_button_label

    def get_context(self, name, value, attrs):
        """
        Build the context passed to the template.

        'value' is expected to be either:
        - a list of list, e.g. [[disp1, val1], [disp2, val2], ...]
        - a single string (which will be parsed into tuples), e.g.:
          "Need help with an account|I need help with my account\n
           A question about an order|I have a question about my order\n
           General question|I have a general question"
        - or None/empty.
        """
        context = super().get_context(name, value, attrs)

        # Normalize to a list of tuples
        tuple_list = self._to_tuple_list(value)

        # In the template, you can iterate over widget['list_items'] to show each tuple
        context['widget']['list_items'] = tuple_list

        # The 'value' displayed in the form is the string version of the tuples
        context['widget']['value'] = self.format_value(tuple_list)

        # Pass the custom labels into the template
        context['widget']['add_button_label'] = self.add_button_label
        context['widget']['remove_button_label'] = self.remove_button_label

        # Include any custom attributes
        context['widget']['attrs'].update(attrs or {})
        return context

    def format_value(self, value):
        """
        Convert a list of list into a string suitable for the form's text area/input.
        Here we join each list (display, value) by '|' and separate items by newlines.
        """
        if not value:
            return ''
        # If we truly have a list of tuples, convert them line by line
        if isinstance(value, list):
            lines = []
            for item in value:
                # Expect each item to be (display_text, value_text)
                if isinstance(item, tuple) and len(item) == 2:
                    lines.append(f"{item[0]}|{item[1]}")
                else:
                    # If it isn't a tuple of length 2, just string it
                    lines.append(str(item))
            return "\n".join(lines)
        # Fallback if it's not a list
        return str(value)

    def value_from_datadict(self, data, files, name):
        """
        Extract the list of lists (e.g. [["1", "2"], ["3", "4"]]) from the POST data.
        """
        raw_values = data.getlist(name)  # e.g. ["1", "2", "3", "4", ...]

        result = []
        i = 0
        while i < len(raw_values):
            display = raw_values[i].strip() if raw_values[i] else ''
            value = ''
            if i + 1 < len(raw_values):
                value = raw_values[i + 1].strip() if raw_values[i + 1] else ''
            result.append([display, value])  # <-- use list, not tuple
            i += 2

        return result

    def _to_list_of_lists(self, value):
        """
        Internal helper: ensure 'value' is a list of [string, string].
        """
        if not value:
            return []
        elif isinstance(value, str):
            # Possibly parse a string, but if you intend to store raw lists,
            # you might just skip this. Otherwise, parse lines:
            lines = value.split('\n')
            pairs = []
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                parts = line.split('|', 1)
                if len(parts) == 2:
                    pairs.append([parts[0].strip(), parts[1].strip()])
                else:
                    pairs.append([parts[0].strip(), ''])
            return pairs
        elif isinstance(value, list):
            # Already a list, ensure each subitem is 2-length
            normalized = []
            for item in value:
                if isinstance(item, (tuple, list)):
                    pair = list(item)  # make sure it's a list
                    # If somehow not length 2, adapt
                    if len(pair) == 1:
                        pair.append('')
                    normalized.append(pair[:2])
                else:
                    # If it's a single value or something else
                    normalized.append([str(item), ''])
            return normalized

        # fallback
        return []

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        # Transform the incoming value into a list-of-lists
        list_of_lists = self._to_list_of_lists(value)

        # For the template iteration:
        context['widget']['list_items'] = list_of_lists
        context['widget']['value'] = list_of_lists  # or some string version
        context['widget']['add_button_label'] = self.add_button_label
        context['widget']['remove_button_label'] = self.remove_button_label
        context['widget']['attrs'].update(attrs or {})
        return context