from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "postgresql+psycopg://crm:crm-local-demo@localhost:5432/crm"
    redis_url: str = "redis://localhost:6379/0"
    cache_ttl: int = 60
    keycloak_issuer: str = "http://localhost:8080/realms/rostelecom-it-school"
    keycloak_jwks_url: str = ""
    keycloak_audience: str = "crm-backend"
    keycloak_client_id: str = "crm-frontend"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    data_dir: Path = Path("data/v2")
    max_upload_mb: int = 20
    integration_mode: str = "mock"
    integration_allowed_hosts: str = ""
    lms_api_url: str = ""
    lms_api_token: str = ""
    website_api_url: str = ""
    website_api_token: str = ""
    seed_demo: bool = True
    testing: bool = False

    @property
    def upload_limit(self):
        return self.max_upload_mb * 1024 * 1024


@lru_cache
def get_settings():
    return Settings()


settings = get_settings()
