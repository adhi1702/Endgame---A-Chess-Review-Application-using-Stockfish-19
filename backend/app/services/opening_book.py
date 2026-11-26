"""Small offline set of common main lines used to mark opening theory moves."""

import chess


_OPENING_LINES = (
    "e4 e5 Nf3 Nc6 Bc4 Bc5",                         # Italian Game
    "e4 e5 Nf3 Nc6 Bb5 a6 Ba4 Nf6 O-O Be7",        # Ruy Lopez
    "e4 e5 Nf3 Nc6 d4 exd4 Nxd4",                  # Scotch Game
    "e4 e5 Nf3 Nc6 Nc3 Nf6",                       # Four Knights
    "e4 c5 Nf3 d6 d4 cxd4 Nxd4 Nf6 Nc3 a6",        # Sicilian Najdorf
    "e4 c5 Nf3 Nc6 d4 cxd4 Nxd4",                  # Sicilian Open
    "e4 e6 d4 d5 Nc3 Nf6",                         # French Defense
    "e4 c6 d4 d5 Nc3 dxe4 Nxe4 Bf5",               # Caro-Kann
    "d4 d5 c4 e6 Nc3 Nf6",                         # Queen's Gambit
    "d4 d5 c4 c6 Nc3 Nf6",                         # Slav Defense
    "d4 Nf6 c4 g6 Nc3 Bg7 e4 d6",                  # King's Indian
    "d4 Nf6 c4 e6 Nc3 Bb4",                        # Nimzo-Indian
    "d4 Nf6 c4 e6 Nf3 b6 g3 Bb7",                  # Queen's Indian
    "c4 e5 Nc3 Nf6",                               # English Opening
    "Nf3 d5 c4",                                    # Reti Opening
    "e4 d6 d4 Nf6 Nc3 g6",                         # Pirc Defense
    "d4 f5 c4 Nf6 g3 e6 Bg2",                      # Dutch Defense
    "d4 d5 Bf4 Nf6 e3 e6 Nf3",                     # London System
    "d4 Nf6 c4 e6 g3 d5 Bg2",                      # Catalan Opening
)


def _to_uci_line(san_line: str) -> tuple[str, ...]:
    board = chess.Board()
    moves = []
    for san in san_line.split():
        move = board.parse_san(san)
        moves.append(move.uci())
        board.push(move)
    return tuple(moves)


_BOOK_LINES = tuple(_to_uci_line(line) for line in _OPENING_LINES)


def is_book_move(moves: list[chess.Move]) -> bool:
    """Return true when the played move continues one of the bundled lines."""
    candidate = tuple(move.uci() for move in moves)
    return any(line[: len(candidate)] == candidate for line in _BOOK_LINES)
