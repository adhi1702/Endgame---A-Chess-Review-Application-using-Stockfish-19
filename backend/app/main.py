from datetime import datetime, timedelta, timezone
import jwt
from fastapi import FastAPI, Depends, HTTPException, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from pwdlib import PasswordHash
from app.core.config import settings
from app.db import Base, engine, get_db
from app.models import User, Game, Move, AnalysisJob, MoveAnalysis, GameAnalysis
from app.schemas import Register, Login, ImportGame
from app.services.pgn import parse_pgn

app = FastAPI(title="Chess Review API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
password_hash = PasswordHash.recommended()

@app.on_event("startup")
def startup():
    # Schema lifecycle is managed explicitly by Alembic migrations.
    pass

def current_user(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer "): raise HTTPException(401, "Authentication required")
    try: subject = jwt.decode(authorization[7:], settings.jwt_secret, algorithms=["HS256"])["sub"]
    except Exception as exc: raise HTTPException(401, "Invalid or expired token") from exc
    user = db.get(User, subject)
    if not user: raise HTTPException(401, "Account not found")
    return user

def token_for(user):
    return jwt.encode({"sub": user.id, "exp": datetime.now(timezone.utc) + timedelta(days=7)}, settings.jwt_secret, algorithm="HS256")

@app.get("/api/health")
def health(): return {"status": "ok"}

@app.post("/api/auth/register")
def register(data: Register, db: Session = Depends(get_db)):
    if db.scalar(select(User).where((User.email == data.email) | (User.username == data.username))): raise HTTPException(409, "Email or username already exists")
    user = User(username=data.username, email=data.email, password_hash=password_hash.hash(data.password)); db.add(user); db.commit(); db.refresh(user)
    return {"token": token_for(user), "user": {"id": user.id, "username": user.username, "email": user.email}}

@app.post("/api/auth/login")
def login(data: Login, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == data.email))
    if not user or not password_hash.verify(data.password, user.password_hash): raise HTTPException(401, "Incorrect email or password")
    return {"token": token_for(user), "user": {"id": user.id, "username": user.username, "email": user.email}}

@app.get("/api/auth/me")
def me(user: User = Depends(current_user)): return {"id": user.id, "username": user.username, "email": user.email}

@app.post("/api/games")
def import_game(data: ImportGame, db: Session = Depends(get_db), user: User = Depends(current_user)):
    parsed = parse_pgn(data.pgn); headers = parsed["headers"]
    game = Game(user_id=user.id, white_player=headers.get("White", "White"), black_player=headers.get("Black", "Black"), result=headers.get("Result", "*"), event=headers.get("Event", "Imported game"), pgn=data.pgn, initial_fen=parsed["initial_fen"], played_at=headers.get("Date"))
    game.moves = [Move(**move) for move in parsed["moves"]]; db.add(game); db.commit(); db.refresh(game)
    return {"id": game.id, "white_player": game.white_player, "black_player": game.black_player, "result": game.result, "event": game.event, "played_at": game.played_at, "move_count": len(game.moves)}

@app.get("/api/games")
def list_games(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), q: str | None = None, db: Session = Depends(get_db), user: User = Depends(current_user)):
    stmt = select(Game).where(Game.user_id == user.id)
    if q: stmt = stmt.where((Game.white_player.ilike(f"%{q}%")) | (Game.black_player.ilike(f"%{q}%")))
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(stmt.order_by(Game.created_at.desc()).offset((page-1)*page_size).limit(page_size)).all()
    return {"items": [{"id": g.id, "white_player": g.white_player, "black_player": g.black_player, "result": g.result, "event": g.event, "played_at": g.played_at, "move_count": len(g.moves)} for g in rows], "total": total, "page": page, "page_size": page_size}

def owned_game(game_id, user, db):
    game = db.scalar(select(Game).where(Game.id == game_id, Game.user_id == user.id))
    if not game: raise HTTPException(404, "Game not found")
    return game

@app.get("/api/games/{game_id}")
def get_game(game_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    g = owned_game(game_id, user, db)
    latest = db.scalar(select(AnalysisJob).where(AnalysisJob.game_id == g.id, AnalysisJob.status == "completed").order_by(AnalysisJob.created_at.desc()))
    rows = db.scalars(select(MoveAnalysis).where(MoveAnalysis.job_id == latest.id)).all() if latest else []
    analysis_by_move = {m.move_id: {"evaluation_before": m.evaluation_before, "evaluation_after": m.evaluation_after, "centipawn_loss": m.centipawn_loss, "classification": m.classification, "best_move_uci": m.best_move_uci, "principal_variation": m.principal_variation} for m in rows}
    summary = db.scalar(select(GameAnalysis).where(GameAnalysis.game_id == g.id).order_by(GameAnalysis.created_at.desc()))
    return {"id": g.id, "white_player": g.white_player, "black_player": g.black_player, "result": g.result, "event": g.event, "played_at": g.played_at, "initial_fen": g.initial_fen, "analysis_summary": {"accuracy_white": summary.accuracy_white, "accuracy_black": summary.accuracy_black, "inaccuracies": summary.inaccuracies, "mistakes": summary.mistakes, "blunders": summary.blunders} if summary else None, "moves": [{"id": m.id, "ply": m.ply, "move_number": m.move_number, "color": m.color, "san": m.san, "uci": m.uci, "fen_after": m.fen_after, "analysis": analysis_by_move.get(m.id)} for m in g.moves]}

@app.put("/api/games/{game_id}")
def replace_game(game_id: str, data: ImportGame, db: Session = Depends(get_db), user: User = Depends(current_user)):
    g = owned_game(game_id, user, db); parsed = parse_pgn(data.pgn); h = parsed["headers"]
    g.pgn = data.pgn; g.white_player = h.get("White", "White"); g.black_player = h.get("Black", "Black"); g.result = h.get("Result", "*"); g.event = h.get("Event", "Imported game"); g.played_at = h.get("Date"); g.initial_fen = parsed["initial_fen"]
    g.moves.clear(); g.moves.extend(Move(**move) for move in parsed["moves"]); db.commit(); return {"id": g.id, "move_count": len(g.moves)}

@app.patch("/api/games/{game_id}")
def patch_game(game_id: str, data: dict, db: Session = Depends(get_db), user: User = Depends(current_user)):
    g = owned_game(game_id, user, db)
    for field in ("white_player", "black_player", "event"):
        if field in data: setattr(g, field, str(data[field])[:255])
    db.commit(); return {"id": g.id, "white_player": g.white_player, "black_player": g.black_player, "event": g.event}

@app.delete("/api/games/{game_id}")
def delete_game(game_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    g = owned_game(game_id, user, db); db.delete(g); db.commit(); return {"deleted": True}

@app.post("/api/games/{game_id}/analysis", status_code=202)
def queue_analysis(game_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    g = owned_game(game_id, user, db)
    active_job = db.scalar(select(AnalysisJob).where(AnalysisJob.game_id == g.id, AnalysisJob.status.in_(["queued", "running"])).order_by(AnalysisJob.created_at.desc()))
    if active_job:
        return {"id": active_job.id, "status": active_job.status, "depth": active_job.depth, "progress": active_job.progress}
    job = AnalysisJob(game_id=g.id, depth=settings.engine_depth); db.add(job); db.commit(); db.refresh(job)
    return {"id": job.id, "status": job.status, "depth": job.depth}

@app.get("/api/analysis-jobs/{job_id}")
def job_status(job_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    job = db.scalar(select(AnalysisJob).join(Game).where(AnalysisJob.id == job_id, Game.user_id == user.id))
    if not job: raise HTTPException(404, "Analysis job not found")
    return {"id": job.id, "status": job.status, "depth": job.depth, "progress": job.progress, "error_message": job.error_message}

@app.get("/api/games/{game_id}/analysis")
def game_analysis(game_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    owned_game(game_id, user, db)
    job = db.scalar(select(AnalysisJob).where(AnalysisJob.game_id == game_id).order_by(AnalysisJob.created_at.desc()))
    if not job: return {"status": "not_started"}
    rows = db.scalars(select(MoveAnalysis).where(MoveAnalysis.job_id == job.id)).all()
    summary = db.scalar(select(GameAnalysis).where(GameAnalysis.job_id == job.id))
    return {"status": job.status, "progress": job.progress, "summary": {"total_moves": summary.total_moves, "inaccuracies": summary.inaccuracies, "mistakes": summary.mistakes, "blunders": summary.blunders, "accuracy_white": summary.accuracy_white, "accuracy_black": summary.accuracy_black} if summary else None, "moves": [{"move_id": m.move_id, "evaluation_before": m.evaluation_before, "evaluation_after": m.evaluation_after, "centipawn_loss": m.centipawn_loss, "classification": m.classification, "best_move_uci": m.best_move_uci, "principal_variation": m.principal_variation} for m in rows]}

@app.get("/api/dashboard/stats")
def dashboard(db: Session = Depends(get_db), user: User = Depends(current_user)):
    games = db.scalars(select(Game).where(Game.user_id == user.id)).all()
    return {"total_games": len(games), "wins": sum(g.result == "1-0" for g in games), "losses": sum(g.result == "0-1" for g in games), "draws": sum(g.result == "1/2-1/2" for g in games), "recent_games": [{"id": g.id, "white_player": g.white_player, "black_player": g.black_player, "result": g.result, "played_at": g.played_at} for g in games[:8]]}
