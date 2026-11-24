from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str = "sqlite:///./chess_review.db"
    jwt_secret: str = "local-development-only-change-me"
    stockfish_path: str = "stockfish"
    engine_threads: int = 2
    engine_hash_mb: int = 256
    engine_depth: int = 12
    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")

settings = Settings()
