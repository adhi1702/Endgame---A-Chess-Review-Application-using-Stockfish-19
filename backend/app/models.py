import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, Integer, Float, ForeignKey, DateTime, UniqueConstraint, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base

def uid(): return str(uuid.uuid4())
def now(): return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    games: Mapped[list["Game"]] = relationship(back_populates="user", cascade="all, delete-orphan")

class Game(Base):
    __tablename__ = "games"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    white_player: Mapped[str] = mapped_column(String(120), default="White")
    black_player: Mapped[str] = mapped_column(String(120), default="Black")
    result: Mapped[str] = mapped_column(String(10), default="*")
    event: Mapped[str] = mapped_column(String(255), default="Imported game")
    source: Mapped[str] = mapped_column(String(40), default="pgn")
    pgn: Mapped[str] = mapped_column(Text)
    initial_fen: Mapped[str] = mapped_column(String(120))
    played_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    user: Mapped[User] = relationship(back_populates="games")
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
    status: Mapped[str] = mapped_column(String(20), default="queued")
    depth: Mapped[int] = mapped_column(Integer)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class MoveAnalysis(Base):
    __tablename__ = "move_analyses"
    __table_args__ = (UniqueConstraint("move_id", "job_id"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    move_id: Mapped[str] = mapped_column(ForeignKey("moves.id", ondelete="CASCADE"), index=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("analysis_jobs.id", ondelete="CASCADE"), index=True)
    evaluation_before: Mapped[float] = mapped_column(Float)
    evaluation_after: Mapped[float] = mapped_column(Float)
    centipawn_loss: Mapped[float] = mapped_column(Float)
    classification: Mapped[str] = mapped_column(String(20))
    best_move_uci: Mapped[str | None] = mapped_column(String(10), nullable=True)
    principal_variation: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
