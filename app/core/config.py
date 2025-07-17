from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
 
    PROJECT_NAME: str = "Variant Context API"
    ASSEMBLY: str = "GRCh38"
    LOGGING_LEVEL: str = "INFO"
    
    ENSEMBL_API_SERVER: str = "https://rest.ensembl.org"
    REACTOME_API_SERVER: str = "https://reactome.org/ContentService"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )

settings = Settings()
