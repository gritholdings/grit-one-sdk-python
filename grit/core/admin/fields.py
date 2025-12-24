from django import forms


class ListField(forms.Field):
    """
    A form field that handles a list of strings.
    """

    def to_python(self, value):
        """
        Convert the input value into a Python list of strings.
        This is called when the form is being validated.
        """
        if not value:
            # Convert empty/None to an empty list
            return []
        if isinstance(value, list):
            # If it's already a list, assume items are strings (or will be validated below)
            return value
        # If it's a comma-separated string (depending on how your widget posts data),
        # split into a list.
        return [item.strip() for item in value.split(',') if item.strip()]

    def validate(self, value):
        """
        Validate that `value` is indeed a list of strings.
        """
        # First call the parent class’s validation (e.g. checks required, etc.)
        super().validate(value)

        # Ensure it's a list
        if not isinstance(value, list):
            raise forms.ValidationError("This field requires a list of strings.")

        # (Optional) Ensure all items are strings
        for item in value:
            if not isinstance(item, str):
                raise forms.ValidationError("All items must be strings.")
            

class ListListField(forms.Field):
    """
    A form field that handles a list of list.
    """

    def to_python(self, value):
        """
        Convert the input value into a Python list of lists.
        This is called when the form is being validated.
        """
        if not value:
            # Convert empty/None to an empty list
            return []
        if isinstance(value, list):
            # If it's already a list, assume items are lists (or will be validated below)
            return value
        # If it's a comma-separated string (depending on how your widget posts data),
        # split into a list.
        return [item.strip() for item in value.split(',') if item.strip()]