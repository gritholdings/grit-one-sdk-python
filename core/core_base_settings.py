"""
Use core_settings.py as settings.py is used for core project settings.
"""
from app import settings


class BaseSettings:
    """Base class for agent settings."""
    # Subclasses can override this to specify their settings key
    SETTINGS_KEY: str = ''
    
    def __init__(self):
        super().__init__()
        # Override with settings from app.settings if available
        if self.SETTINGS_KEY:
            settings_key = self.SETTINGS_KEY
        else:
            raise ValueError("SETTINGS_KEY must be defined in subclasses.")
        
        if hasattr(settings, settings_key):
            override_settings = getattr(settings, settings_key, {})
            for key, value in override_settings.items():
                if hasattr(self, key):
                    setattr(self, key, value)