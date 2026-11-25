import chess
import chess.engine
import fcntl
import os
import tempfile
from contextlib import contextmanager
from app.core.config import settings
from app.services.classification import classify_loss


@contextmanager
def _engine_lock():
    """Serialize UCI access across the API and background worker processes."""
    path = os.path.join(tempfile.gettempdir(), "stockfish-review-engine.lock")
    with open(path, "w") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def analyze_position(fen: str):
    board = chess.Board(fen)
    if not board.is_valid():
        raise ValueError("The position is not a valid chess position")
    if board.is_game_over(claim_draw=True):
        score = board.outcome(claim_draw=True).winner
        evaluation = 0 if score is None else (1000 if score else -1000)
        return {"evaluation": evaluation, "best_move_uci": None, "principal_variation": []}

    with _engine_lock():
        engine = chess.engine.SimpleEngine.popen_uci(settings.stockfish_path)
        try:
            engine.configure({"Threads": settings.engine_threads, "Hash": settings.engine_hash_mb})
            result = engine.analyse(board, chess.engine.Limit(depth=min(settings.engine_depth, 12)))
            white_score = result["score"].white().score(mate_score=100000)
            return {
                "evaluation": (white_score or 0) / 100,
                "best_move_uci": result.get("pv", [None])[0].uci() if result.get("pv") else None,
                "principal_variation": [move.uci() for move in result.get("pv", [])],
            }
        finally:
            engine.quit()

def analyze_game(game, job, db):
    with _engine_lock():
        engine = chess.engine.SimpleEngine.popen_uci(settings.stockfish_path)
        try:
            engine.configure({"Threads": settings.engine_threads, "Hash": settings.engine_hash_mb})
            board = chess.Board(game.initial_fen)
            total = len(game.moves)
            analyses = []
            for index, move_row in enumerate(game.moves):
                before = engine.analyse(board, chess.engine.Limit(depth=job.depth))
                best_score = before["score"].pov(board.turn)
                best_move = before.get("pv", [None])[0]
                move = chess.Move.from_uci(move_row.uci)
                mover = board.turn
                board.push(move)
                before_cp = best_score.score(mate_score=100000)
                if board.is_checkmate():
                    after_cp = 100000
                elif board.is_game_over(claim_draw=True):
                    after_cp = 0
                else:
                    after = engine.analyse(board, chess.engine.Limit(depth=job.depth))
                    after_cp = after["score"].pov(mover).score(mate_score=100000)
                before_cp = before_cp if before_cp is not None else 0
                after_cp = after_cp if after_cp is not None else 0
                loss = max(0, before_cp - after_cp)
                record = {"move_id": move_row.id, "job_id": job.id, "evaluation_before": before_cp/100, "evaluation_after": after_cp/100, "centipawn_loss": loss, "classification": classify_loss(loss), "best_move_uci": best_move.uci() if best_move else None, "principal_variation": [m.uci() for m in before.get("pv", [])]}
                analyses.append(record)
                job.progress = int((index + 1) * 100 / total)
                db.add(job); db.commit()
            return analyses
        finally:
            engine.quit()
