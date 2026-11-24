import io
import chess.pgn
from fastapi import HTTPException

def parse_pgn(raw: str):
    try:
        game = chess.pgn.read_game(io.StringIO(raw))
        if game is None: raise ValueError("No game found")
        if game.errors: raise ValueError("; ".join(str(e) for e in game.errors))
        board = game.board()
        moves = []
        for ply, move in enumerate(game.mainline_moves(), start=1):
            if move not in board.legal_moves: raise ValueError(f"Illegal move at ply {ply}")
            san = board.san(move)
            color = "white" if board.turn else "black"
            board.push(move)
            moves.append({"ply": ply, "move_number": (ply + 1)//2, "color": color, "san": san, "uci": move.uci(), "fen_after": board.fen()})
        if not moves: raise ValueError("The PGN contains no moves")
        headers = game.headers
        return {"headers": dict(headers), "moves": moves, "initial_fen": game.board().fen()}
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid PGN: {exc}") from exc
