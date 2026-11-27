from datetime import datetime, timezone
import httpx
from app.core.config import settings

BASE = "https://api.chess.com/pub"

class ChessComError(Exception):
    def __init__(self, status: int, message: str):
        self.status = status
        super().__init__(message)

class ChessComClient:
    def __init__(self):
        self.client = httpx.Client(timeout=settings.chesscom_timeout_seconds, headers={
            "User-Agent": settings.chesscom_user_agent,
            "Accept": "application/json, application/x-chess-pgn, text/plain",
        }, follow_redirects=True)

    def get_json(self, path: str):
        response = self.client.get(f"{BASE}{path}")
        if response.status_code == 429:
            raise ChessComError(429, "Chess.com is rate limiting requests; try again later")
        if response.status_code >= 400:
            raise ChessComError(response.status_code, "Chess.com profile or archive was not found")
        return response.json()

    def profile(self, username: str):
        return self.get_json(f"/player/{username.lower()}")

    def stats(self, username: str):
        try: return self.get_json(f"/player/{username.lower()}/stats")
        except ChessComError as exc:
            if exc.status == 404: return {}
            raise

    def archives(self, username: str):
        return self.get_json(f"/player/{username.lower()}/games/archives").get("archives", [])

    def games(self, archive_url: str):
        # Archive links in the public index are HTTPS URLs under api.chess.com;
        # reject unexpected hosts before following an externally supplied URL.
        if not archive_url.startswith("https://api.chess.com/pub/player/"):
            raise ChessComError(422, "Chess.com archive URL is invalid")
        response = self.client.get(archive_url, headers={"Accept": "application/json"})
        if response.status_code == 429: raise ChessComError(429, "Chess.com is rate limiting requests; try again later")
        if response.status_code >= 400: raise ChessComError(response.status_code, "Chess.com archive is unavailable")
        # PubAPI archive endpoint serves JSON even when PGN links are available.
        payload = response.json()
        return payload.get("games", [])

def parse_archive_month(url: str):
    try:
        year, month = url.rstrip("/").split("/")[-2:]
        return int(year), int(month)
    except (ValueError, IndexError):
        return 0, 0

def played_at_from_epoch(timestamp):
    if not timestamp: return None
    return datetime.fromtimestamp(int(timestamp), tz=timezone.utc).isoformat()
