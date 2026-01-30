class ModelMetadataMixin:
    def update_metadata(self, key, value):
        if self.metadata is None:
            self.metadata = {}
        self.metadata[key] = value
        self.save()