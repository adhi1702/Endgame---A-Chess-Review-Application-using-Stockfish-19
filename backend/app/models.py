import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, Integer, Float, ForeignKey, DateTime, UniqueConstraint, JSON, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base

def uid(): return str(uuid.uuid4())
def now(): return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    display_name: Mapped[str] = mapped_column(String(100), default="Player", server_default="Player")
    profile_picture: Mapped[str | None] = mapped_column(Text, nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    games: Mapped[list["Game"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    auth_accounts: Mapped[list["AuthAccount"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    connected_accounts: Mapped[list["ConnectedAccount"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    preferences: Mapped["UserPreference | None"] = relationship(back_populates="user", cascade="all, delete-orphan", uselist=False)


class AuthAccount(Base):
    __tablename__ = "auth_accounts"
    __table_args__ = (UniqueConstraint("provider", "provider_user_id", name="uq_auth_provider_subject"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(30), default="google")
    provider_user_id: Mapped[str] = mapped_column(String(255))
    provider_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    user: Mapped[User] = relationship(back_populates="auth_accounts")


class ConnectedAccount(Base):
    __tablename__ = "connected_accounts"
    __table_args__ = (UniqueConstraint("user_id", "provider", name="uq_connected_user_provider"), UniqueConstraint("provider", "external_username", name="uq_connected_provider_username"))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(30), default="chesscom")
    external_username: Mapped[str] = mapped_column(String(100))
    external_player_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    profile_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    connection_status: Mapped[str] = mapped_column(String(30), default="active")
    sync_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    user: Mapped[User] = relationship(back_populates="connected_accounts")
    games: Mapped[list["Game"]] = relationship(back_populates="connected_account")


class ChessRating(Base):
    __tablename__ = "chess_ratings"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    connected_account_id: Mapped[str | None] = mapped_column(ForeignKey("connected_accounts.id", ondelete="SET NULL", name="fk_games_connected_account_id"), nullable=True, index=True)
    game_type: Mapped[str] = mapped_column(String(20))
    rating: Mapped[int] = mapped_column(Integer)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    source: Mapped[str] = mapped_column(String(30), default="chesscom")


class UserPreference(Base):
    __tablename__ = "user_preferences"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    board_theme: Mapped[str] = mapped_column(String(50), default="green", server_default="green")
    piece_theme: Mapped[str] = mapped_column(String(50), default="classic", server_default="classic")
    default_analysis_depth: Mapped[int] = mapped_column(Integer, default=16, server_default="16")
    multipv: Mapped[int] = mapped_column(Integer, default=3, server_default="3")
    auto_analyze: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    auto_sync: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    user: Mapped[User] = relationship(back_populates="preferences")


class UserSession(Base):
    __tablename__ = "user_sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    session_token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    csrf_token_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AccountLinkChallenge(Base):
    __tablename__ = "account_link_challenges"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SyncJob(Base):
    __tablename__ = "sync_jobs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    connected_account_id: Mapped[str] = mapped_column(ForeignKey("connected_accounts.id", ondelete="CASCADE"), index=True)
    sync_type: Mapped[str] = mapped_column(String(30), default="manual")
    status: Mapped[str] = mapped_column(String(30), default="queued", index=True)
    games_found: Mapped[int] = mapped_column(Integer, default=0)
    games_imported: Mapped[int] = mapped_column(Integer, default=0)
    games_skipped: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Game(Base):
    __tablename__ = "games"
    __table_args__ = (
        UniqueConstraint("connected_account_id", "external_game_id", name="uq_game_connected_external"),
        Index("ix_games_user_played", "user_id", "played_at"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    white_player: Mapped[str] = mapped_column(String(120), default="White")
    black_player: Mapped[str] = mapped_column(String(120), default="Black")
    result: Mapped[str] = mapped_column(String(10), default="*")
    event: Mapped[str] = mapped_column(String(255), default="Imported game")
    source: Mapped[str] = mapped_column(String(40), default="pgn")
    connected_account_id: Mapped[str | None] = mapped_column(ForeignKey("connected_accounts.id", ondelete="SET NULL"), nullable=True, index=True)
    external_game_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    white_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    black_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    user_color: Mapped[str | None] = mapped_column(String(10), nullable=True)
    opening_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    eco_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    time_control: Mapped[str | None] = mapped_column(String(50), nullable=True)
    pgn: Mapped[str] = mapped_column(Text)
    initial_fen: Mapped[str] = mapped_column(String(120))
    played_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    user: Mapped[User] = relationship(back_populates="games")
    connected_account: Mapped[ConnectedAccount | None] = relationship(back_populates="games")
    moves: Mapped[list["Move"]] = relationship(back_populates="game", cascade="all, delete-orphan", order_by="Move.ply")
    jobs: Mapped[list["AnalysisJob"]] = relationship(back_populates="game", cascade="all, delete-orphan")

class Move(Base):
    __tablename__ = "moves"
    __table_args__ = (UniqueConstraint("game_id", "ply"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    game_id: Mapped[str] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"), index=True)
    move_number: Mapped[int] = mapped_column(Integer)
    ply: Mapped[int] = mapped_column(Integer)
    color: Mapped[str] = mapped_column(String(5))
    san: Mapped[str] = mapped_column(String(20))
    uci: Mapped[str] = mapped_column(String(10))
    fen_after: Mapped[str] = mapped_column(String(120))
    game: Mapped[Game] = relationship(back_populates="moves")

class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    game_id: Mapped[str] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="queued", index=True)
    depth: Mapped[int] = mapped_column(Integer)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    engine_name: Mapped[str] = mapped_column(String(50), default="Stockfish", server_default="Stockfish")
    engine_version: Mapped[str | None] = mapped_column(String(30), nullable=True)
    engine_config: Mapped[dict] = mapped_column(JSON, default=dict, server_default="{}")
    total_moves: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    analysis_status: Mapped[str] = mapped_column(String(30), default="queued", server_default="queued")
    white_cpl: Mapped[float | None] = mapped_column(Float, nullable=True)
    black_cpl: Mapped[float | None] = mapped_column(Float, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    game: Mapped[Game] = relationship(back_populates="jobs")

class GameAnalysis(Base):
    __tablename__ = "game_analyses"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    game_id: Mapped[str] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"), index=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("analysis_jobs.id", ondelete="CASCADE"), unique=True)
    total_moves: Mapped[int] = mapped_column(Integer)
    inaccuracies: Mapped[int] = mapped_column(Integer, default=0)
    mistakes: Mapped[int] = mapped_column(Integer, default=0)
    blunders: Mapped[int] = mapped_column(Integer, default=0)
    accuracy_white: Mapped[float | None] = mapped_column(Float, nullable=True)
    accuracy_black: Mapped[float | None] = mapped_column(Float, nullable=True)
    white_cpl: Mapped[float | None] = mapped_column(Float, nullable=True)
    black_cpl: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class MoveAnalysis(Base):
    __tablename__ = "move_analyses"
    __table_args__ = (UniqueConstraint("move_id", "job_id"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    move_id: Mapped[str] = mapped_column(ForeignKey("moves.id", ondelete="CASCADE"), index=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("analysis_jobs.id", ondelete="CASCADE"), index=True)
    evaluation_before: Mapped[float] = mapped_column(Float)
    evaluation_after: Mapped[float] = mapped_column(Float)
    ply: Mapped[int | None] = mapped_column(Integer, nullable=True)
    move_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    color: Mapped[str | None] = mapped_column(String(10), nullable=True)
    played_move: Mapped[str | None] = mapped_column(String(10), nullable=True)
    centipawn_loss: Mapped[float] = mapped_column(Float)
    mate_before: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mate_after: Mapped[int | None] = mapped_column(Integer, nullable=True)
    classification: Mapped[str] = mapped_column(String(20))
    best_move_uci: Mapped[str | None] = mapped_column(String(10), nullable=True)
    principal_variation: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
