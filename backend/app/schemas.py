from pydantic import BaseModel, EmailStr, Field, ConfigDict, model_validator
from typing import Literal

class Register(BaseModel):
    username: str = Field(min_length=2, max_length=80)
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)

class Login(BaseModel):
    email: EmailStr
    password: str

class ImportGame(BaseModel):
    pgn: str = Field(min_length=10, max_length=500_000)

class PositionAnalysisRequest(BaseModel):
    fen: str = Field(min_length=10, max_length=100)

class GoogleAuthRequest(BaseModel):
    credential: str = Field(min_length=20, max_length=10_000)
    link_challenge: str | None = Field(default=None, min_length=20, max_length=200)

class LegacyLinkRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

class ProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    country: str | None = Field(default=None, max_length=100)
    bio: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_display_name(self):
        if self.display_name is not None and not self.display_name.strip():
            raise ValueError("Display name cannot be empty")
        return self

class PreferencesUpdate(BaseModel):
    board_theme: str | None = Field(default=None, min_length=1, max_length=50)
    piece_theme: str | None = Field(default=None, min_length=1, max_length=50)
    default_analysis_depth: int | None = Field(default=None, ge=8, le=30)
    multipv: int | None = Field(default=None, ge=1, le=5)
    auto_analyze: bool | None = None
    auto_sync: bool | None = None

class ChessComConnect(BaseModel):
    username: str = Field(min_length=3, max_length=100, pattern=r"^[A-Za-z0-9_-]+$")

class SyncRequest(BaseModel):
    sync_mode: Literal["initial", "incremental", "historical", "manual"] = "incremental"

class GameListFilters(BaseModel):
    result: Literal["win", "draw", "loss"] | None = None
    color: Literal["white", "black"] | None = None
    review_status: Literal["not_started", "queued", "running", "completed", "failed"] | None = None
    source: Literal["pgn", "chesscom"] | None = None

class GameOut(BaseModel):
    id: str
    white_player: str
    black_player: str
    result: str
    event: str
    played_at: str | None
    move_count: int
    model_config = ConfigDict(from_attributes=True)
