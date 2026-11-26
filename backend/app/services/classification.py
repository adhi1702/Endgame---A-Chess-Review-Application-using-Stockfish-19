def classify_move(
    cp_loss: float,
    *,
    is_book: bool = False,
    before_cp: float = 0,
    is_best: bool = False,
    best_move_gap: float = 0,
    brilliant_sacrifice: bool = False,
) -> str:
    """Classify a move from engine loss and a few explicit tactical signals.

    Thresholds are review heuristics, not an official rating system.
    """
    if is_book:
        return "Book"
    if brilliant_sacrifice and is_best and cp_loss <= 10:
        return "Brilliant"
    if is_best and best_move_gap >= 150:
        return "Great"
    if before_cp >= 300 and 100 <= cp_loss < 300:
        return "Miss"
    if cp_loss <= 10:
        return "Best"
    if cp_loss <= 30:
        return "Excellent"
    if cp_loss <= 80:
        return "Good"
    if cp_loss <= 150:
        return "Inaccuracy"
    if cp_loss <= 300:
        return "Mistake"
    return "Blunder"
