from datetime import datetime, timedelta, timezone
import logging
import re
import secrets
import threading
import jwt
import chess
from fastapi import FastAPI, Depends, HTTPException, Header, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, func, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from pwdlib import PasswordHash
from app.core.config import settings
from app.db import Base, engine, get_db
from app.models import User, Game, Move, AnalysisJob, MoveAnalysis, GameAnalysis, AuthAccount, UserPreference, UserSession, AccountLinkChallenge, ConnectedAccount, SyncJob, ChessRating
from app.schemas import ImportGame, PositionAnalysisRequest, GoogleAuthRequest, LegacyLinkRequest, ProfileUpdate, PreferencesUpdate, ChessComConnect, SyncRequest
from app.services.pgn import parse_pgn
from app.engine.stockfish import analyze_position
from app.worker import recover_interrupted_jobs, run_once
from app.services.auth_service import authenticate_request, clear_session_cookies, find_google_account, hash_secret, issue_session, user_payload, verify_google_credential
from app.services.chesscom import ChessComClient, ChessComError

app = FastAPI(title="Chess Review API", version="0.2.0")
app.add_middleware(CORSMiddleware, allow_origins=settings.allowed_origins, allow_credentials=True, allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"], allow_headers=["Authorization", "Content-Type", "X-CSRF-Token"])
password_hash = PasswordHash.recommended()
logger = logging.getLogger("analysis-worker")
worker_stop = threading.Event()
worker_wakeup = threading.Event()
worker_thread: threading.Thread | None = None


def _consume_analysis_jobs():
    while not worker_stop.is_set():
        worker_wakeup.clear()
        try:
            worked = run_once()
        except Exception:
            logger.exception("Analysis worker loop failed")
            worked = False
        if not worked:
            worker_wakeup.wait(timeout=2)

@app.on_event("startup")
def startup():
    # Schema lifecycle is managed explicitly by Alembic migrations. Local mode
    # uses an in-process consumer; Celery mode is drained by the worker service.
    global worker_thread
    recover_interrupted_jobs()
    if not settings.celery_enabled:
        worker_stop.clear()
        worker_wakeup.set()
    if not settings.celery_enabled and (not worker_thread or not worker_thread.is_alive()):
        worker_thread = threading.Thread(
            target=_consume_analysis_jobs,
            name="analysis-worker",
            daemon=True,
        )
        worker_thread.start()


@app.on_event("shutdown")
def shutdown():
    if settings.celery_enabled:
        return
    worker_stop.set()
    worker_wakeup.set()
    if worker_thread and worker_thread.is_alive():
        worker_thread.join(timeout=5)

def current_user(request: Request, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    return authenticate_request(request, authorization, db)

def token_for(user):
    return jwt.encode({"sub": user.id, "exp": datetime.now(timezone.utc) + timedelta(days=7)}, settings.jwt_secret, algorithm="HS256")

@app.get("/api/health")
def health(): return {"status": "ok"}

@app.get("/api/health/ready")
def readiness(db: Session = Depends(get_db)):
    try:
        db.execute(select(1))
    except Exception as exc:
        raise HTTPException(503, "Database is unavailable") from exc
    return {"status": "ready", "database": "ok"}


def require_frontend_origin(request: Request):
    origin = request.headers.get("origin", "").rstrip("/")
    if not origin or origin not in settings.allowed_origins:
        raise HTTPException(403, "Request origin is not allowed")


def _preference_payload(preferences: UserPreference):
    return {"board_theme": preferences.board_theme, "piece_theme": preferences.piece_theme,
            "default_analysis_depth": preferences.default_analysis_depth, "multipv": preferences.multipv,
            "auto_analyze": preferences.auto_analyze, "auto_sync": preferences.auto_sync}


@app.post("/api/v1/auth/google")
def google_login(data: GoogleAuthRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    require_frontend_origin(request)
    claims = verify_google_credential(data.credential)
    subject = str(claims["sub"])
    email = str(claims["email"]).strip().lower()
    account = find_google_account(db, subject)
    if account and not data.link_challenge:
        existing_user = db.get(User, account.user_id)
        if existing_user and existing_user.email.lower() != email:
            raise HTTPException(409, detail={"code": "google_account_conflict", "message": "This Google identity is already linked to a different email account."})
    if data.link_challenge:
        now_utc = datetime.now(timezone.utc)
        challenge = db.scalar(select(AccountLinkChallenge).where(
            AccountLinkChallenge.token_hash == hash_secret(data.link_challenge),
            AccountLinkChallenge.used_at.is_(None),
            AccountLinkChallenge.expires_at > now_utc.replace(tzinfo=None),
        ))
        if not challenge:
            raise HTTPException(401, "Account link challenge expired; verify your existing account again")
        user = db.get(User, challenge.user_id)
        if not user or not user.is_active:
            raise HTTPException(401, "Account is unavailable")
        if user.email.lower() != email:
            raise HTTPException(409, detail={"code": "google_email_mismatch", "message": "Use the Google account with the same email as the existing account you verified."})
        if account and account.user_id != user.id:
            raise HTTPException(409, "This Google account is already linked to another profile")
        claimed = db.execute(update(AccountLinkChallenge).where(
            AccountLinkChallenge.id == challenge.id,
            AccountLinkChallenge.used_at.is_(None),
            AccountLinkChallenge.expires_at > now_utc.replace(tzinfo=None),
        ).values(used_at=now_utc.replace(tzinfo=None)), execution_options={"synchronize_session": False})
        if claimed.rowcount != 1:
            db.rollback()
            raise HTTPException(409, "Account link challenge was already used")
        if not account:
            db.add(AuthAccount(user_id=user.id, provider="google", provider_user_id=subject, provider_email=email))
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise HTTPException(409, "This Google account was linked in another request; sign in again") from exc
    elif account:
        user = db.get(User, account.user_id)
        if not user or not user.is_active:
            raise HTTPException(401, "Account is unavailable")
    else:
        user = db.scalar(select(User).where(func.lower(User.email) == email))
        if user:
            raise HTTPException(status_code=409, detail={"code": "legacy_account_link_required", "message": "Verify your existing account password once to safely link this Google account and keep your saved games."})
        base = re.sub(r"[^a-z0-9_]+", "_", email.split("@", 1)[0].lower()).strip("_")[:64] or "player"
        username = base
        while db.scalar(select(User.id).where(User.username == username)):
            username = f"{base[:55]}_{secrets.token_hex(4)}"
        user = User(username=username, email=email, password_hash=None,
                    display_name=str(claims.get("name") or username)[:100],
                    profile_picture=claims.get("picture"))
        db.add(user)
        db.flush()
        db.add(AuthAccount(user_id=user.id, provider="google", provider_user_id=subject, provider_email=email))
        db.add(UserPreference(user_id=user.id))
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise HTTPException(409, "Account was created in another sign-in request; try again") from exc
    issue_session(db, user, response)
    return {"user": user_payload(user)}


@app.post("/api/v1/auth/link/legacy")
def start_legacy_link(data: LegacyLinkRequest, request: Request, db: Session = Depends(get_db)):
    require_frontend_origin(request)
    user = db.scalar(select(User).where(func.lower(User.email) == str(data.email).lower()))
    if not user or not user.password_hash or not password_hash.verify(data.password, user.password_hash):
        raise HTTPException(401, "Email or password is incorrect")
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    db.execute(update(AccountLinkChallenge).where(AccountLinkChallenge.user_id == user.id, AccountLinkChallenge.used_at.is_(None)).values(used_at=now_utc), execution_options={"synchronize_session": False})
    raw_challenge = secrets.token_urlsafe(36)
    db.add(AccountLinkChallenge(
        user_id=user.id,
        token_hash=hash_secret(raw_challenge),
        expires_at=now_utc + timedelta(minutes=5),
    ))
    db.commit()
    return {"link_challenge": raw_challenge, "expires_in": 300}


@app.get("/api/v1/auth/me")
def current_profile(request: Request, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    # Refresh the readable CSRF cookie for sessions created before CSRF
    # protection was enabled or when the browser discarded that cookie.
    raw_session = request.cookies.get(settings.session_cookie_name)
    if raw_session:
        csrf = request.cookies.get(settings.csrf_cookie_name)
        session = db.scalar(select(UserSession).where(
            UserSession.session_token_hash == hash_secret(raw_session),
            UserSession.revoked_at.is_(None),
            UserSession.expires_at > datetime.now(timezone.utc),
        ))
        if session and (not csrf or hash_secret(csrf) != session.csrf_token_hash):
            raw_csrf = secrets.token_urlsafe(32)
            session.csrf_token_hash = hash_secret(raw_csrf)
            db.commit()
            try:
                user = db.get(User, session.user_id)
                if not user or not user.is_active: return Response(status_code=204)
                from fastapi.responses import JSONResponse
                response = JSONResponse({"user": user_payload(user)})
                response.set_cookie(settings.csrf_cookie_name, raw_csrf, httponly=False,
                    max_age=settings.session_ttl_hours * 3600, secure=settings.session_cookie_secure,
                    samesite=settings.normalized_cookie_samesite, path="/api")
                return response
            except Exception:
                db.rollback()
    try:
        user = authenticate_request(request, authorization, db)
    except HTTPException as exc:
        if exc.status_code in (401, 403):
            return Response(status_code=204)
        raise
    return {"user": user_payload(user)}


@app.post("/api/v1/auth/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db), user: User = Depends(current_user)):
    raw = request.cookies.get(settings.session_cookie_name)
    if raw:
        session = db.scalar(select(UserSession).where(UserSession.session_token_hash == hash_secret(raw), UserSession.user_id == user.id))
        if session:
            session.revoked_at = datetime.now(timezone.utc)
            db.commit()
    clear_session_cookies(response)
    return {"logged_out": True}


@app.post("/api/v1/auth/logout-all")
def logout_all(response: Response, db: Session = Depends(get_db), user: User = Depends(current_user)):
    db.execute(update(UserSession).where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None)).values(revoked_at=datetime.now(timezone.utc)))
    db.commit()
    clear_session_cookies(response)
    return {"logged_out": True}


@app.get("/api/v1/auth/sessions")
def list_sessions(request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
    raw = request.cookies.get(settings.session_cookie_name, "")
    current = db.scalar(select(UserSession).where(UserSession.session_token_hash == hash_secret(raw))) if raw else None
    rows = db.scalars(select(UserSession).where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None), UserSession.expires_at > datetime.now(timezone.utc)).order_by(UserSession.created_at.desc())).all()
    return {"sessions": [{"id": row.id, "created_at": row.created_at.isoformat(), "expires_at": row.expires_at.isoformat(), "current": bool(current and current.id == row.id)} for row in rows]}


@app.get("/api/v1/users/profile")
def read_profile(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return {"profile": user_payload(user), "created_at": user.created_at.isoformat(),
            "games_imported": db.scalar(select(func.count(Game.id)).where(Game.user_id == user.id)) or 0,
            "games_reviewed": db.scalar(select(func.count(func.distinct(GameAnalysis.game_id))).where(GameAnalysis.game_id.in_(select(Game.id).where(Game.user_id == user.id)))) or 0}


@app.patch("/api/v1/users/profile")
def update_profile(data: ProfileUpdate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    for field, value in data.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(user, field, value.strip() if isinstance(value, str) else value)
    if not user.display_name.strip(): raise HTTPException(422, "Display name cannot be empty")
    db.commit()
    return {"profile": user_payload(user)}


@app.get("/api/v1/users/preferences")
def read_preferences(user: User = Depends(current_user), db: Session = Depends(get_db)):
    preferences = db.scalar(select(UserPreference).where(UserPreference.user_id == user.id))
    if not preferences:
        preferences = UserPreference(user_id=user.id)
        db.add(preferences)
        db.commit()
        db.refresh(preferences)
    return {"preferences": _preference_payload(preferences)}


@app.patch("/api/v1/users/preferences")
def update_preferences(data: PreferencesUpdate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    preferences = db.scalar(select(UserPreference).where(UserPreference.user_id == user.id))
    if not preferences:
        preferences = UserPreference(user_id=user.id)
        db.add(preferences)
    values = data.model_dump(exclude_unset=True)
    if "auto_sync" in values: values["auto_sync"] = values.pop("auto_sync")
    for field, value in values.items():
        if value is not None:
            setattr(preferences, field, value)
    db.commit()
    db.refresh(preferences)
    return {"preferences": _preference_payload(preferences)}


def _chesscom_error(exc: ChessComError):
    status = 503 if exc.status >= 500 else (429 if exc.status == 429 else 422)
    raise HTTPException(status, str(exc)) from exc


@app.post("/api/v1/integrations/chesscom")
def connect_chesscom(data: ChessComConnect, user: User = Depends(current_user), db: Session = Depends(get_db)):
    client = ChessComClient()
    try:
        profile = client.profile(data.username)
        stats = client.stats(data.username)
    except ChessComError as exc: _chesscom_error(exc)
    owner = db.scalar(select(ConnectedAccount).where(ConnectedAccount.provider == "chesscom", func.lower(ConnectedAccount.external_username) == data.username.lower(), ConnectedAccount.user_id != user.id))
    if owner: raise HTTPException(409, "This Chess.com username is already connected to another account")
    account = db.scalar(select(ConnectedAccount).where(ConnectedAccount.user_id == user.id, ConnectedAccount.provider == "chesscom"))
    created_account = account is None
    if not account:
        account = ConnectedAccount(user_id=user.id, provider="chesscom", external_username=data.username)
        db.add(account)
        db.flush()
    account.external_username = profile.get("username", data.username)
    account.external_player_id = str(profile.get("player_id") or "") or None
    account.profile_url = profile.get("url")
    account.avatar_url = profile.get("avatar")
    account.connection_status = "active"
    bullet = (stats.get("chess_bullet") or {}).get("last") or {}
    blitz = (stats.get("chess_blitz") or {}).get("last") or {}
    rapid = (stats.get("chess_rapid") or {}).get("last") or {}
    if created_account:
        for kind, entry in (("bullet", bullet), ("blitz", blitz), ("rapid", rapid)):
            if entry.get("rating"):
                db.add(ChessRating(user_id=user.id, connected_account_id=account.id, game_type=kind, rating=int(entry["rating"])))
    db.commit(); db.refresh(account)
    return {"account": {"id": account.id, "username": account.external_username, "profile_url": account.profile_url, "avatar_url": account.avatar_url, "last_synced_at": account.last_synced_at}, "ratings": {"bullet": bullet.get("rating"), "blitz": blitz.get("rating"), "rapid": rapid.get("rating")}}


@app.get("/api/v1/integrations/chesscom")
def chesscom_status(user: User = Depends(current_user), db: Session = Depends(get_db)):
    account = db.scalar(select(ConnectedAccount).where(ConnectedAccount.user_id == user.id, ConnectedAccount.provider == "chesscom"))
    if not account: return {"connected": False}
    return {"connected": True, "account": {"id": account.id, "username": account.external_username, "profile_url": account.profile_url, "avatar_url": account.avatar_url, "last_synced_at": account.last_synced_at, "sync_enabled": account.sync_enabled}}


def _sync_chesscom(db: Session, job_id: str):
    job = db.get(SyncJob, job_id)
    if not job: return
    account = db.get(ConnectedAccount, job.connected_account_id)
    if not account: job.status = "failed"; job.error_message = "Connected account was removed"; db.commit(); return
    job.status = "running"; job.started_at = datetime.now(timezone.utc); db.commit()
    client = ChessComClient()
    try:
        archives = client.archives(account.external_username)
        # Initial sync is bounded to the most recent three monthly archives.
        selected = archives[-3:] if job.sync_type == "initial" else archives[-1:]
        for archive_url in selected:
            for item in client.games(archive_url):
                job.games_found += 1
                external_id = str(item.get("url") or item.get("uuid") or "")
                if external_id and db.scalar(select(Game.id).where(Game.connected_account_id == account.id, Game.external_game_id == external_id)):
                    job.games_skipped += 1; continue
                pgn = item.get("pgn")
                if not pgn: job.games_skipped += 1; continue
                try: parsed = parse_pgn(pgn)
                except Exception: job.games_skipped += 1; continue
                white, black = item.get("white") or {}, item.get("black") or {}
                user_color = "white" if str(white.get("username", "")).lower() == account.external_username.lower() else "black" if str(black.get("username", "")).lower() == account.external_username.lower() else None
                game = Game(user_id=job.user_id, connected_account_id=account.id, external_game_id=external_id or None,
                    source="chesscom", white_player=white.get("username", parsed["headers"].get("White", "White")),
                    black_player=black.get("username", parsed["headers"].get("Black", "Black")),
                    result=parsed["headers"].get("Result", "*"), event=parsed["headers"].get("Event", "Chess.com game"),
                    pgn=pgn, initial_fen=parsed["initial_fen"], moves=[Move(**move) for move in parsed["moves"]],
                    played_at=played_at_from_epoch(item.get("end_time")), white_rating=white.get("rating"), black_rating=black.get("rating"), user_color=user_color,
                    time_control=str(item.get("time_control") or "")[:50] or None, eco_code=item.get("eco"), opening_name=item.get("name"))
                db.add(game)
                if job.sync_type == "initial":
                    preferences = db.scalar(select(UserPreference).where(UserPreference.user_id == job.user_id))
                    if preferences and preferences.auto_analyze:
                        game.analysis_auto_depth = preferences.default_analysis_depth
                try:
                    db.flush()
                    if getattr(game, "analysis_auto_depth", None):
                        db.add(AnalysisJob(game_id=game.id, depth=game.analysis_auto_depth))
                    job.games_imported += 1
                except IntegrityError:
                    db.rollback()
                    job = db.get(SyncJob, job_id)
                    job.games_skipped += 1
                    continue
            db.commit()
        account.last_synced_at = datetime.now(timezone.utc)
        job.status = "completed"; job.completed_at = datetime.now(timezone.utc); db.commit()
    except Exception as exc:
        db.rollback(); job = db.get(SyncJob, job_id); job.status = "failed"; job.error_message = str(exc)[:1000]; job.completed_at = datetime.now(timezone.utc); db.commit()


@app.post("/api/v1/integrations/chesscom/sync", status_code=202)
def sync_chesscom(data: SyncRequest, user: User = Depends(current_user), db: Session = Depends(get_db)):
    account = db.scalar(select(ConnectedAccount).where(ConnectedAccount.user_id == user.id, ConnectedAccount.provider == "chesscom"))
    if not account: raise HTTPException(404, "Connect a Chess.com account first")
    if db.scalar(select(SyncJob.id).where(SyncJob.connected_account_id == account.id, SyncJob.status.in_(("queued", "running")))):
        raise HTTPException(409, "A Chess.com sync is already running for this account")
    job = SyncJob(user_id=user.id, connected_account_id=account.id, sync_type="initial" if data.sync_mode == "initial" else "incremental")
    db.add(job); db.commit(); db.refresh(job)
    # Redis/Celery is used when enabled; local development needs no Redis.
    if settings.celery_enabled:
        from app.tasks import run_chesscom_sync
        run_chesscom_sync.delay(job.id)
    else:
        threading.Thread(target=_run_sync_background, args=(job.id,), daemon=True).start()
    return {"id": job.id, "status": job.status}


def _run_sync_background(job_id: str):
    from app.db import SessionLocal
    with SessionLocal() as db: _sync_chesscom(db, job_id)


@app.get("/api/v1/integrations/chesscom/sync/{job_id}")
def chesscom_sync_status(job_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    job = db.scalar(select(SyncJob).where(SyncJob.id == job_id, SyncJob.user_id == user.id))
    if not job: raise HTTPException(404, "Sync job not found")
    return {"id": job.id, "status": job.status, "games_found": job.games_found, "games_imported": job.games_imported, "games_skipped": job.games_skipped, "error_message": job.error_message}

@app.post("/api/auth/register")
def register():
    raise HTTPException(410, "Password registration has been replaced by Google sign-in")

@app.post("/api/auth/login")
def login():
    raise HTTPException(410, "Use Google sign-in. Existing accounts can be linked once from the sign-in page.")

@app.get("/api/auth/me")
def me(user: User = Depends(current_user)): return {"id": user.id, "username": user.username, "email": user.email}

@app.post("/api/games")
@app.post("/api/v1/games")
def import_game(data: ImportGame, db: Session = Depends(get_db), user: User = Depends(current_user)):
    parsed = parse_pgn(data.pgn); headers = parsed["headers"]
    preferences = db.scalar(select(UserPreference).where(UserPreference.user_id == user.id))
    white = headers.get("White", "White"); black = headers.get("Black", "Black")
    color = "white" if white.lower() == user.username.lower() else "black" if black.lower() == user.username.lower() else None
    game = Game(user_id=user.id, white_player=white, black_player=black, result=headers.get("Result", "*"), event=headers.get("Event", "Imported game"), pgn=data.pgn, initial_fen=parsed["initial_fen"], played_at=headers.get("Date"), user_color=color, source="pgn", white_rating=_rating(headers.get("WhiteElo")), black_rating=_rating(headers.get("BlackElo")), opening_name=headers.get("Opening"), eco_code=headers.get("ECO"), time_control=headers.get("TimeControl"))
    game.moves = [Move(**move) for move in parsed["moves"]]; db.add(game); db.flush()
    if preferences and preferences.auto_analyze:
        db.add(AnalysisJob(game_id=game.id, depth=preferences.default_analysis_depth))
    db.commit(); db.refresh(game)
    if preferences and preferences.auto_analyze:
        if settings.celery_enabled:
            from app.tasks import drain_analysis_queue
            drain_analysis_queue.delay()
        else:
            worker_wakeup.set()
    return {"id": game.id, "white_player": game.white_player, "black_player": game.black_player, "result": game.result, "event": game.event, "played_at": game.played_at, "move_count": len(game.moves)}

@app.get("/api/games")
@app.get("/api/v1/games")
def list_games(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), q: str | None = None, result: str | None = None, color: str | None = None, review_status: str | None = None, source: str | None = None, db: Session = Depends(get_db), user: User = Depends(current_user)):
    stmt = select(Game).where(Game.user_id == user.id)
    if result in {"win", "draw", "loss"}:
        if result == "draw": stmt = stmt.where(Game.result == "1/2-1/2")
        else:
            white_result, black_result = ("1-0", "0-1") if result == "win" else ("0-1", "1-0")
            stmt = stmt.where(((Game.user_color == "white") & (Game.result == white_result)) | ((Game.user_color == "black") & (Game.result == black_result)))
    if source: stmt = stmt.where(Game.source == source)
    if color in {"white", "black"}: stmt = stmt.where(Game.user_color == color)
    if q:
        stmt = stmt.where((Game.white_player.ilike(f"%{q}%")) | (Game.black_player.ilike(f"%{q}%")) | (Game.event.ilike(f"%{q}%")) | (Game.opening_name.ilike(f"%{q}%")))
    if review_status in {"not_started", "queued", "running", "completed", "failed"}:
        latest_job = select(AnalysisJob.status).where(AnalysisJob.game_id == Game.id).order_by(AnalysisJob.created_at.desc()).limit(1).scalar_subquery()
        if review_status == "not_started": stmt = stmt.where(~select(AnalysisJob.id).where(AnalysisJob.game_id == Game.id).exists())
        else: stmt = stmt.where(latest_job == review_status)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(stmt.order_by(Game.created_at.desc()).offset((page-1)*page_size).limit(page_size)).all()
    return {"items": [{"id": g.id, "white_player": g.white_player, "black_player": g.black_player, "result": g.result, "event": g.event, "played_at": g.played_at, "move_count": len(g.moves), "source": g.source, "user_color": g.user_color, "white_rating": g.white_rating, "black_rating": g.black_rating, "opening_name": g.opening_name, "eco_code": g.eco_code, "time_control": g.time_control} for g in rows], "total": total, "page": page, "page_size": page_size}

def owned_game(game_id, user, db):
    game = db.scalar(select(Game).where(Game.id == game_id, Game.user_id == user.id))
    if not game: raise HTTPException(404, "Game not found")
    return game

def _rating(value):
    try: return int(value) if value else None
    except (TypeError, ValueError): return None

@app.get("/api/games/{game_id}")
@app.get("/api/v1/games/{game_id}")
def get_game(game_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    g = owned_game(game_id, user, db)
    latest = db.scalar(select(AnalysisJob).where(AnalysisJob.game_id == g.id, AnalysisJob.status == "completed").order_by(AnalysisJob.created_at.desc()))
    rows = db.scalars(select(MoveAnalysis).where(MoveAnalysis.job_id == latest.id)).all() if latest else []
    analysis_by_move = {m.move_id: {"evaluation_before": m.evaluation_before, "evaluation_after": m.evaluation_after, "centipawn_loss": m.centipawn_loss, "classification": m.classification, "best_move_uci": m.best_move_uci, "principal_variation": m.principal_variation} for m in rows}
    summary = db.scalar(select(GameAnalysis).join(AnalysisJob, GameAnalysis.job_id == AnalysisJob.id).where(GameAnalysis.game_id == g.id, AnalysisJob.status == "completed").order_by(GameAnalysis.created_at.desc()))
    return {"id": g.id, "white_player": g.white_player, "black_player": g.black_player, "result": g.result, "event": g.event, "played_at": g.played_at, "initial_fen": g.initial_fen, "source": g.source, "user_color": g.user_color, "white_rating": g.white_rating, "black_rating": g.black_rating, "opening_name": g.opening_name, "eco_code": g.eco_code, "time_control": g.time_control, "analysis_summary": {"accuracy_white": summary.accuracy_white, "accuracy_black": summary.accuracy_black, "inaccuracies": summary.inaccuracies, "mistakes": summary.mistakes, "blunders": summary.blunders} if summary else None, "moves": [{"id": m.id, "ply": m.ply, "move_number": m.move_number, "color": m.color, "san": m.san, "uci": m.uci, "fen_after": m.fen_after, "analysis": analysis_by_move.get(m.id)} for m in g.moves]}

@app.post("/api/games/{game_id}/position-analysis")
@app.post("/api/v1/games/{game_id}/position-analysis")
def position_analysis(game_id: str, data: PositionAnalysisRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    owned_game(game_id, user, db)
    try:
        chess.Board(data.fen)
        return analyze_position(data.fen)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc

@app.put("/api/games/{game_id}")
@app.put("/api/v1/games/{game_id}")
def replace_game(game_id: str, data: ImportGame, db: Session = Depends(get_db), user: User = Depends(current_user)):
    g = owned_game(game_id, user, db); parsed = parse_pgn(data.pgn); h = parsed["headers"]
    g.pgn = data.pgn; g.white_player = h.get("White", "White"); g.black_player = h.get("Black", "Black"); g.result = h.get("Result", "*"); g.event = h.get("Event", "Imported game"); g.played_at = h.get("Date"); g.initial_fen = parsed["initial_fen"]
    g.moves.clear(); g.moves.extend(Move(**move) for move in parsed["moves"]); db.commit(); return {"id": g.id, "move_count": len(g.moves)}

@app.patch("/api/games/{game_id}")
@app.patch("/api/v1/games/{game_id}")
def patch_game(game_id: str, data: dict, db: Session = Depends(get_db), user: User = Depends(current_user)):
    g = owned_game(game_id, user, db)
    for field in ("white_player", "black_player", "event"):
        if field in data: setattr(g, field, str(data[field])[:255])
    db.commit(); return {"id": g.id, "white_player": g.white_player, "black_player": g.black_player, "event": g.event}

@app.delete("/api/games/{game_id}")
@app.delete("/api/v1/games/{game_id}")
def delete_game(game_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    g = owned_game(game_id, user, db); db.delete(g); db.commit(); return {"deleted": True}

@app.post("/api/games/{game_id}/analysis", status_code=202)
@app.post("/api/v1/games/{game_id}/analysis", status_code=202)
def queue_analysis(game_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    g = owned_game(game_id, user, db)
    active_job = db.scalar(select(AnalysisJob).where(AnalysisJob.game_id == g.id, AnalysisJob.status.in_(["queued", "running"])).order_by(AnalysisJob.created_at.desc()))
    if active_job:
        return {"id": active_job.id, "status": active_job.status, "depth": active_job.depth, "progress": active_job.progress}
    job = AnalysisJob(game_id=g.id, depth=settings.engine_depth); db.add(job); db.commit(); db.refresh(job)
    if settings.celery_enabled:
        from app.tasks import drain_analysis_queue
        drain_analysis_queue.delay()
    else:
        worker_wakeup.set()
    return {"id": job.id, "status": job.status, "depth": job.depth}

@app.get("/api/analysis-jobs/{job_id}")
@app.get("/api/v1/analysis-jobs/{job_id}")
def job_status(job_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    job = db.scalar(select(AnalysisJob).join(Game).where(AnalysisJob.id == job_id, Game.user_id == user.id))
    if not job: raise HTTPException(404, "Analysis job not found")
    return {"id": job.id, "status": job.status, "depth": job.depth, "progress": job.progress, "error_message": job.error_message}

@app.get("/api/games/{game_id}/analysis")
@app.get("/api/v1/games/{game_id}/analysis")
def game_analysis(game_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    owned_game(game_id, user, db)
    job = db.scalar(select(AnalysisJob).where(AnalysisJob.game_id == game_id).order_by(AnalysisJob.created_at.desc()))
    if not job: return {"status": "not_started"}
    rows = db.scalars(select(MoveAnalysis).where(MoveAnalysis.job_id == job.id)).all()
    summary = db.scalar(select(GameAnalysis).where(GameAnalysis.job_id == job.id)) if job.status == "completed" else None
    return {"status": job.status, "progress": job.progress, "summary": {"total_moves": summary.total_moves, "inaccuracies": summary.inaccuracies, "mistakes": summary.mistakes, "blunders": summary.blunders, "accuracy_white": summary.accuracy_white, "accuracy_black": summary.accuracy_black} if summary else None, "moves": [{"move_id": m.move_id, "evaluation_before": m.evaluation_before, "evaluation_after": m.evaluation_after, "centipawn_loss": m.centipawn_loss, "classification": m.classification, "best_move_uci": m.best_move_uci, "principal_variation": m.principal_variation} for m in rows]}

@app.get("/api/dashboard/stats")
@app.get("/api/v1/dashboard/stats")
def dashboard(db: Session = Depends(get_db), user: User = Depends(current_user)):
    games = db.scalars(select(Game).where(Game.user_id == user.id)).all()
    return {"total_games": len(games), "wins": sum((g.user_color == "white" and g.result == "1-0") or (g.user_color == "black" and g.result == "0-1") for g in games), "losses": sum((g.user_color == "white" and g.result == "0-1") or (g.user_color == "black" and g.result == "1-0") for g in games), "draws": sum(g.result == "1/2-1/2" for g in games), "recent_games": [{"id": g.id, "white_player": g.white_player, "black_player": g.black_player, "result": g.result, "played_at": g.played_at} for g in games[:8]]}


@app.get("/api/v1/analytics/openings")
def opening_analytics(db: Session = Depends(get_db), user: User = Depends(current_user)):
    games = db.scalars(select(Game).where(Game.user_id == user.id)).all()
    counts = __import__("collections").Counter((game.opening_name or "Unclassified") for game in games)
    return {"openings": [{"name": name, "count": count} for name, count in counts.most_common(20)]}


@app.get("/api/v1/analytics")
def analytics(db: Session = Depends(get_db), user: User = Depends(current_user)):
    games = db.scalars(select(Game).where(Game.user_id == user.id)).all()
    reviewed = db.scalars(select(GameAnalysis).join(AnalysisJob, AnalysisJob.id == GameAnalysis.job_id).where(GameAnalysis.game_id.in_([game.id for game in games]), AnalysisJob.status == "completed")).all() if games else []
    accuracies = [value for analysis in reviewed for value in (analysis.accuracy_white, analysis.accuracy_black) if value is not None]
    color_counts = {"white": sum(g.user_color == "white" for g in games), "black": sum(g.user_color == "black" for g in games)}
    results = {"wins": sum(g.result in ("1-0", "0-1") and ((g.user_color == "white" and g.result == "1-0") or (g.user_color == "black" and g.result == "0-1")) for g in games),
               "draws": sum(g.result == "1/2-1/2" for g in games),
               "losses": sum(g.result in ("1-0", "0-1") and ((g.user_color == "white" and g.result == "0-1") or (g.user_color == "black" and g.result == "1-0")) for g in games)}
    return {"total_games": len(games), "reviewed_games": len(reviewed), "average_accuracy": round(sum(accuracies)/len(accuracies), 1) if accuracies else None,
            "results": results, "color_counts": color_counts,
            "openings": [{"name": name, "count": count} for name, count in sorted(__import__("collections").Counter(g.opening_name for g in games if g.opening_name).items(), key=lambda x: x[1], reverse=True)[:10]]}


@app.get("/api/v1/analytics/performance")
def performance_analytics(db: Session = Depends(get_db), user: User = Depends(current_user)):
    games = db.scalars(select(Game).where(Game.user_id == user.id)).all()
    if not games: return {"monthly": [], "opponents": []}
    reviews = db.scalars(select(GameAnalysis).join(AnalysisJob, AnalysisJob.id == GameAnalysis.job_id).where(GameAnalysis.game_id.in_([game.id for game in games]), AnalysisJob.status == "completed")).all()
    monthly = {}
    for game in games:
        date = game.played_at or ""
        month = date[:7] if len(date) >= 7 else "Unknown"
        bucket = monthly.setdefault(month, {"month": month, "games": 0, "wins": 0, "draws": 0, "losses": 0})
        bucket["games"] += 1
        outcome = "draw" if game.result == "1/2-1/2" else ("win" if (game.user_color == "white" and game.result == "1-0") or (game.user_color == "black" and game.result == "0-1") else "loss")
        bucket[outcome + "s" if outcome != "draw" else "draws"] += 1
    opponents = __import__("collections").Counter((game.black_player if game.user_color == "white" else game.white_player) for game in games if game.user_color)
    return {"monthly": [monthly[key] for key in sorted(monthly)], "reviewed_games": len(reviews), "opponents": [{"name": name, "games": count} for name, count in opponents.most_common(10)]}
