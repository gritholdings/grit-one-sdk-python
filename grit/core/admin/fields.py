from django import forms


class ListField(forms.Field):
    def to_python(self, value):
        if not value:
            return []
        if isinstance(value, list):
            return value
        return [item.strip() for item in value.split(',') if item.strip()]
    def validate(self, value):
        super().validate(value)
        if not isinstance(value, list):
            raise forms.ValidationError("This field requires a list of strings.")
        for item in value:
            if not isinstance(item, str):
                raise forms.ValidationError("All items must be strings.")


class ListListField(forms.Field):
    def to_python(self, value):
        if not value:
            return []
        if isinstance(value, list):
            return value
        return [item.strip() for item in value.split(',') if item.strip()]