import time
import logging
import fcntl
import os
import tempfile
from datetime import datetime, timezone
from sqlalchemy import select, update
from app.db import SessionLocal
from app.models import AnalysisJob, Game, MoveAnalysis, GameAnalysis
from app.engine.stockfish import analyze_game

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("analysis-worker")


def _worker_lock_file():
    path = os.path.join(tempfile.gettempdir(), "stockfish-review-worker.lock")
    return open(path, "w")


def recover_interrupted_jobs():
    """Requeue jobs left running by a stopped API/worker process."""
    lock_file = _worker_lock_file()
    try:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 0
        db = SessionLocal()
        try:
            recovered = db.execute(
                update(AnalysisJob)
                .where(AnalysisJob.status == "running")
                .values(status="queued", progress=0, started_at=None, error_message=None)
            )
            db.commit()
            if recovered.rowcount:
                logger.warning("Requeued %s interrupted analysis job(s)", recovered.rowcount)
            return recovered.rowcount or 0
        finally:
            db.close()
    finally:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        lock_file.close()

def run_once():
    lock_file = _worker_lock_file()
    try:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        return _run_once_locked()
    finally:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        lock_file.close()


def _run_once_locked():
    db = SessionLocal()
    job = None
    try:
        job_id = db.scalar(
            select(AnalysisJob.id)
            .where(AnalysisJob.status == "queued")
            .order_by(AnalysisJob.created_at)
            .limit(1)
        )
        if not job_id:
            return False
        # Claim with a conditional UPDATE. This also works on SQLite, where
        # SELECT ... FOR UPDATE is ignored, and avoids duplicate processing if
        # the API's built-in worker and a standalone worker run together.
        claimed = db.execute(
            update(AnalysisJob)
            .where(AnalysisJob.id == job_id, AnalysisJob.status == "queued")
            .values(status="running", started_at=datetime.now(timezone.utc))
        )
        db.commit()
        if claimed.rowcount != 1:
            return True
        job = db.get(AnalysisJob, job_id)
        logger.info("Starting analysis job %s for game %s at depth %s", job.id, job.game_id, job.depth)
        db.refresh(job)
        game = db.get(Game, job.game_id)
        records = analyze_game(game, job, db)
        for record in records: db.add(MoveAnalysis(**record))
        losses = [r["centipawn_loss"] for r in records]
        white = [r["centipawn_loss"] for i, r in enumerate(records) if i % 2 == 0]
        black = [r["centipawn_loss"] for i, r in enumerate(records) if i % 2 == 1]
        # Heuristic review score (0-100), based on average centipawn loss; not a chess rating.
        accuracy = lambda values: round(max(0, min(100, 100 - sum(values)/len(values)/10)), 1) if values else None
        db.add(GameAnalysis(game_id=game.id, job_id=job.id, total_moves=len(records), inaccuracies=sum(r["classification"] == "Inaccuracy" for r in records), mistakes=sum(r["classification"] == "Mistake" for r in records), blunders=sum(r["classification"] == "Blunder" for r in records), accuracy_white=accuracy(white), accuracy_black=accuracy(black)))
        job.status = "completed"; job.progress = 100; job.completed_at = datetime.now(timezone.utc); db.commit()
        logger.info("Completed analysis job %s", job.id)
        return True
    except Exception as exc:
        db.rollback()
        logger.exception("Analysis job failed: %s", exc)
        if job:
            job.status = "failed"; job.error_message = str(exc)[:2000]; job.completed_at = datetime.now(timezone.utc); db.commit()
        return True
    finally: db.close()

if __name__ == "__main__":
    while True:
        worked = run_once()
        if not worked: time.sleep(2)
