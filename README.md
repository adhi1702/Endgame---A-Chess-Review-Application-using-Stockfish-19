# Endgame — Chess Review

A local chess game review platform built with React, FastAPI, PostgreSQL and Stockfish. PGN import, account authentication, game history, move navigation, engine-backed analysis jobs and move classifications are included in the initial implementation.

## Requirements

- Python 3.12+
- Node.js 20+
- Stockfish installed locally (Apple Silicon: `brew install stockfish`)

SQLite is used by default, so PostgreSQL and Docker are optional for local use.

## Configure and start

1. Copy `.env.example` to `.env`:

   ```sh
   cp .env.example .env
   ```

2. Generate a private JWT secret and replace the sample value in `.env`:

   ```sh
   python3 -c 'import secrets; print(secrets.token_hex(32))'
   ```

   Keep the generated value private. The repository ignores `.env`.

3. Install Stockfish and check its path:

   ```sh
   brew install stockfish
   which stockfish
   ```

   Put the returned path in `STOCKFISH_PATH` in `.env`.

4. Prepare the API and local SQLite database:

   ```sh
   cd backend
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   alembic upgrade head
   uvicorn app.main:app --reload
   ```

5. In another terminal, start the analysis worker from `backend` with the virtual environment enabled: `python -m app.worker`.
6. Start the frontend: `cd frontend && npm install && npm run dev`.
7. Open http://localhost:5173. The API runs at http://localhost:8000 and its interactive docs are at `/docs`.

## Engine configuration

Set `STOCKFISH_PATH`, `ENGINE_THREADS`, `ENGINE_HASH_MB` and `ENGINE_DEPTH` in `.env`. Defaults are intentionally conservative. The engine runs in the dedicated worker and analysis requests are queued in SQLite. Stockfish is installed locally and is not bundled with this repository. PostgreSQL can be used by changing `DATABASE_URL` and installing its service separately.

## API overview

Authentication: `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`.

Games: `GET /api/games`, `POST /api/games` with `{"pgn":"..."}`, `GET|PUT|PATCH|DELETE /api/games/{id}`. Game list accepts `page`, `page_size` and player search `q`.

Analysis: `POST /api/games/{id}/analysis`, `GET /api/games/{id}/analysis`, `GET /api/analysis-jobs/{id}`. Dashboard: `GET /api/dashboard/stats`.

Every game and job endpoint requires `Authorization: Bearer <token>` and checks user ownership. Passwords use Argon2 hashing; authentication uses signed JWTs. Run schema updates with Alembic (`alembic upgrade head`); the API does not create tables on startup.

## Review scores

Move loss is measured in centipawns from the perspective of the player who made the move, comparing the best score for the pre-move position with the played continuation. Mate scores are mapped to a large centipawn scale for classification. Current default loss bands are Best ≤10, Excellent ≤30, Good ≤80, Inaccuracy ≤150, Mistake ≤300 and Blunder >300 cp. The summary accuracy is a simple, documented heuristic (`100 - average centipawn loss / 10`, clamped to 0–100); it is a review aid, not an official chess rating.

## Current scope

This is the first implementation pass. The dashboard, authentication, PGN import, move navigation and engine-backed review are wired. Detailed statistics pages, profile/engine settings UI and automated test suites still need to be completed. SQLite is the local default; PostgreSQL can be configured for deployment.
