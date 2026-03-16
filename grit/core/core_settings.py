from typing import List
from grit.core.core_base_settings import BaseSettings


class CoreSettings(BaseSettings):
    SETTINGS_KEY = 'CORE_SETTINGS'
    SUBDOMAIN_NAME: str = 'www'
    DOMAIN_NAME: str = 'localhost'
    PLATFORM_NAME: str = 'platform'
    TIME_ZONE: str = 'UTC'
    AWS_RDS_ENDPOINT: str = ''
    AWS_PROFILE: str = ''
    AWS_ACCOUNT_ID: str = ''
    AWS_REGION: str = 'us-east-1'
    IMAGE_NAME: str = ''
    ECR_REPOSITORY_NAME: str = ''
    AZURE_ACR_REGISTRY_NAME: str = ''
    AZURE_ACR_REPOSITORY_NAME: str = ''
    ADDITIONAL_INSTALLED_APPS: List[str] = []
    def __init__(self):
        self.ADDITIONAL_INSTALLED_APPS = []
        super().__init__()
core_settings = CoreSettings()