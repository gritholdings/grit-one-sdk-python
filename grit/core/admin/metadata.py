class MetadataMixin:
    metadata_fields = ()
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and isinstance(self.instance.metadata, dict):
            for metadata_field in self.metadata_fields:
                if metadata_field in self.fields:
                    self.fields[metadata_field].initial = self.instance.metadata.get(metadata_field, "")
    def save(self, commit=True):
        instance = super().save(commit=False)
        if instance.metadata is None:
            instance.metadata = {}
        for metadata_field in self.metadata_fields:
            instance.metadata[metadata_field] = self.cleaned_data.get(metadata_field, "")
        if commit:
            instance.save()
        return instance
