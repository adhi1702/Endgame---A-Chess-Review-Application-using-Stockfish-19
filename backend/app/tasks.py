from celery import shared_task
from sqlalchemy import select
from app.db import SessionLocal
from app.models import ConnectedAccount, UserPreference, SyncJob, AnalysisJob, Game

@shared_task(name="app.tasks.drain_analysis_queue")
def drain_analysis_queue():
    from app.worker import run_once
    count = 0
    while run_once(): count += 1
    return count

@shared_task(name="app.tasks.auto_analyze_unreviewed")
def auto_analyze_unreviewed():
    with SessionLocal() as db:
        rows = db.execute(select(UserPreference.user_id, UserPreference.default_analysis_depth)
                          .where(UserPreference.auto_analyze.is_(True))).all()
        created = 0
        for user_id, depth in rows:
            games = db.scalars(select(Game).where(Game.user_id == user_id)).all()
            for game in games:
                exists = db.scalar(select(AnalysisJob.id).where(AnalysisJob.game_id == game.id, AnalysisJob.status.in_(("queued", "running", "completed"))))
                if not exists:
                    db.add(AnalysisJob(game_id=game.id, depth=depth)); created += 1
        db.commit()
        return created

@shared_task(name="app.tasks.run_chesscom_sync")
def run_chesscom_sync(job_id: str):
    from app.main import _sync_chesscom
    with SessionLocal() as db:
        _sync_chesscom(db, job_id)

@shared_task(name="app.tasks.sync_due_accounts")
def sync_due_accounts():
    from datetime import datetime, timedelta, timezone
    run_ids = []
    with SessionLocal() as db:
        rows = db.execute(select(ConnectedAccount, UserPreference).join(UserPreference, UserPreference.user_id == ConnectedAccount.user_id).where(ConnectedAccount.sync_enabled.is_(True), UserPreference.auto_sync.is_(True))).all()
        queued = 0
        for account, _ in rows:
            if account.last_synced_at and account.last_synced_at > datetime.now(timezone.utc) - timedelta(hours=12):
                continue
            duplicate = db.scalar(select(SyncJob.id).where(SyncJob.connected_account_id == account.id, SyncJob.status.in_(("queued", "running"))))
            if duplicate: continue
            job = SyncJob(user_id=account.user_id, connected_account_id=account.id, sync_type="incremental")
            db.add(job); db.flush(); run_ids.append(job.id); queued += 1
        db.commit()
    for job_id in run_ids:
        run_chesscom_sync.delay(job_id)
    return queued
