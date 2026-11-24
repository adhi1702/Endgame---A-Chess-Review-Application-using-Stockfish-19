def classify_loss(cp_loss: float) -> str:
    """Centipawn loss from mover's perspective: 0-10 best, 10-30 excellent, 30-80 good; 80/150/300+ are inaccuracy/mistake/blunder."""
    if cp_loss <= 10: return "Best"
    if cp_loss <= 30: return "Excellent"
    if cp_loss <= 80: return "Good"
    if cp_loss <= 150: return "Inaccuracy"
    if cp_loss <= 300: return "Mistake"
    return "Blunder"
