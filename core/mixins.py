class ModelMetadataMixin:
    """
    A mixin to provide a reusable method for updating a 'metadata' JSONField.
    Assumes that your model has an attribute called `metadata`.
    """

    def update_metadata(self, key, value):
        """
        Updates the metadata dictionary with the given key-value pair,
        then saves the model.
        """
        if self.metadata is None:
            self.metadata = {}
        self.metadata[key] = value
        self.save()