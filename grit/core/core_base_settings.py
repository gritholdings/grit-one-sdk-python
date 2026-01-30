from app import settings


class BaseSettings:
    SETTINGS_KEY: str = ''
    def __init__(self):
        super().__init__()
        if self.SETTINGS_KEY:
            settings_key = self.SETTINGS_KEY
        else:
            raise ValueError("SETTINGS_KEY must be defined in subclasses.")
        if hasattr(settings, settings_key):
            override_settings = getattr(settings, settings_key, {})
            for key, value in override_settings.items():
                if hasattr(self, key):
                    setattr(self, key, value)