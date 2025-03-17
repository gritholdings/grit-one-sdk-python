"""Metadata mixin"""


class MetadataMixin:
    """
    A mixin for handling metadata fields in ModelForms.
    Maps form fields to specific keys in a JSON/dict metadata field.
    metadata_fields - override this in subclasses to specify which fields to map.

    Example:
    ```
    class CourseAdminForm(MetadataMixin, forms.ModelForm):
    # A regular Django form field, but NOT a real model field
    additional_comment = forms.CharField(
        label="Additional Comment",
        required=False,
        help_text="Any additional comments about the course."
    )

    metadata_fields = ('additional_comment',)

    class Meta:
        model = Course
        fields = ['metadata']
    ```
    """
    metadata_fields = ()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set initial values for all metadata-mapped fields
        if self.instance and isinstance(self.instance.metadata, dict):
            for metadata_field in self.metadata_fields:
                if metadata_field in self.fields:
                    self.fields[metadata_field].initial = self.instance.metadata.get(metadata_field, "")

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Ensure metadata is a dict
        if instance.metadata is None:
            instance.metadata = {}

        # Update metadata with values from mapped fields
        for metadata_field in self.metadata_fields:
            instance.metadata[metadata_field] = self.cleaned_data.get(metadata_field, "")

        if commit:
            instance.save()
        return instance
