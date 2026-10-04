from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/documents"
    elastic_url: str = "http://localhost:9200"
    elastic_index: str = "documents"
    csv_path: str = "data/posts.csv"
    search_limit: int = 20


settings = Settings()
