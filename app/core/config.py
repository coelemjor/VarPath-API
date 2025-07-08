import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr
from pathlib import Path

# Defines project root to allow for consistent file path resolution.
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    """
    Centralized application settings, loaded from environment variables or a .env file.
    Provides a single, validated source of truth for all configuration.
    """
    PROJECT_NAME: str = "Variant Context API"
    ASSEMBLY: str = "GRCh38"
    LOGGING_LEVEL: str = "INFO"

    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str
    DB_PASSWORD: SecretStr # SecretStr type prevents accidental logging of the password.
    DB_NAME: str

    @property
    def DATABASE_CONNINFO(self) -> str:
        """Computes the database connection string from other settings."""
        return f"dbname={self.DB_NAME} user={self.DB_USER} password={self.DB_PASSWORD.get_secret_value()} host={self.DB_HOST} port={self.DB_PORT}"

    REACTOME_MAP_FILE: Path = PROJECT_ROOT / "data/Ensembl2Reactome_All_Levels.txt.gz"
    ALPHAMISSENSE_FILE: Path = PROJECT_ROOT / "data/AlphaMissense_hg38.tsv.gz"
    
    AM_TABLE_NAME: str = "alphamissense_hg38"
    
    ENSEMBL_API_SERVER: str = "https://rest.ensembl.org"

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )

# Global settings instance to be imported by other modules.
settings = Settings()
