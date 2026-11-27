from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str = "sqlite:///./chess_review.db"
    jwt_secret: str = "local-development-only-change-me"
    stockfish_path: str = "stockfish"
    engine_threads: int = 1
    engine_hash_mb: int = 128
    engine_depth: int = 16
    engine_multipv: int = 3
    google_client_id: str = ""
    session_cookie_name: str = "stockfish_review_session"
    session_cookie_secure: bool = False
    session_cookie_samesite: str = "lax"
    session_ttl_hours: int = 168
    csrf_cookie_name: str = "stockfish_review_csrf"
    frontend_origins: str = "http://localhost:5173"
    google_auth_enabled: bool = True
    redis_url: str = "redis://localhost:6379/0"
    celery_enabled: bool = False
    chesscom_user_agent: str = "StockfishReview/1.0"
    chesscom_timeout_seconds: int = 20
    model_config = SettingsConfigDict(env_file="../.env", extra="ignore", case_sensitive=False)

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip().rstrip("/") for origin in self.frontend_origins.split(",") if origin.strip()]

    @property
    def normalized_cookie_samesite(self) -> str:
        value = self.session_cookie_samesite.lower()
        if value not in {"lax", "strict", "none"}:
            return "lax"
        if value == "none" and not self.session_cookie_secure:
            return "lax"
        return value

settings = Settings()
