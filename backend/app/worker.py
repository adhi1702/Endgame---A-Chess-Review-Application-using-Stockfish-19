import time
import logging
from datetime import datetime, timezone
from sqlalchemy import select
from app.db import SessionLocal
from app.models import AnalysisJob, Game, MoveAnalysis, GameAnalysis
from app.engine.stockfish import analyze_game

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("analysis-worker")

def run_once():
    db = SessionLocal()
    try:
        job = db.scalar(select(AnalysisJob).where(AnalysisJob.status == "queued").order_by(AnalysisJob.created_at).with_for_update(skip_locked=True))
        if not job: return False
        logger.info("Starting analysis job %s for game %s at depth %s", job.id, job.game_id, job.depth)
        job.status = "running"; job.started_at = datetime.now(timezone.utc); db.commit(); db.refresh(job)
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
        if 'job' in locals() and job:
            job.status = "failed"; job.error_message = str(exc)[:2000]; job.completed_at = datetime.now(timezone.utc); db.commit()
        return True
    finally: db.close()

if __name__ == "__main__":
    while True:
        worked = run_once()
        if not worked: time.sleep(2)
