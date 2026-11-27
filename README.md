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

2. Generate and set a private `JWT_SECRET` in `.env` (kept for temporary compatibility with older local bearer tokens):

   ```sh
   python3 -c 'import secrets; print(secrets.token_hex(32))'
   ```

   Keep the generated value private. The repository ignores `.env`.

3. Create a Google Cloud OAuth web client ID, add `http://localhost:5173` as an authorized JavaScript origin, and copy the client ID to both `GOOGLE_CLIENT_ID` and `VITE_GOOGLE_CLIENT_ID` in `.env`. Google sign-in will not work until this is set.

4. Install Stockfish and check its path:

   ```sh
   brew install stockfish
   which stockfish
   ```

   Put the returned path in `STOCKFISH_PATH` in `.env`.

5. Prepare the API and local SQLite database:

   ```sh
   cd backend
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   alembic upgrade head
   uvicorn app.main:app --reload
   ```

6. Start the frontend: `cd frontend && npm install && npm run dev`.
7. Open http://localhost:5173. The API runs at http://localhost:8000 and its interactive docs are at `/docs`.

## Engine configuration

Set `STOCKFISH_PATH`, `ENGINE_THREADS`, `ENGINE_HASH_MB` and `ENGINE_DEPTH` in `.env`. Defaults are intentionally conservative. In local mode the API starts the analysis worker automatically; no separate worker terminal is needed. In Celery mode Redis handles queued work. Stockfish is installed locally and is not bundled with this repository.

## API overview

Authentication: Google sign-in at `/api/v1/auth/google`; session cookies are opaque, server-side, and CSRF protected. Existing password accounts can be linked once by proving the old password from the sign-in screen. Their games stay attached to the same account.

Games: `GET /api/games`, `POST /api/games` with `{"pgn":"..."}`, `GET|PUT|PATCH|DELETE /api/games/{id}`. Game list accepts `page`, `page_size` and player search `q`.

Analysis: `POST /api/games/{id}/analysis`, `GET /api/games/{id}/analysis`, `GET /api/analysis-jobs/{id}`. Dashboard: `GET /api/dashboard/stats`.

Versioned game endpoints are also available under `/api/v1`. Chess.com uses its public read-only API and can sync the last three monthly archives from Settings. SQLite and an in-process background runner are used for local development. Docker Compose provides PostgreSQL, Redis, API, Celery worker, and Celery Beat for a service setup. Run schema updates with Alembic (`alembic upgrade head`); the API does not create tables on startup.

Google Identity Services needs `http://localhost:5173` authorized in the Google Cloud OAuth client configuration. For a deployed HTTPS environment, set `SESSION_COOKIE_SECURE=true`, provide strong database credentials and secrets, and set `FRONTEND_ORIGINS` to the deployed frontend origin.

## Review scores

Move loss is measured in centipawns from the perspective of the player who made the move, comparing the best score for the pre-move position with the played continuation. Standard labels use these default bands: Best ≤10, Excellent ≤30, Good ≤80, Inaccuracy ≤150, Mistake ≤300 and Blunder >300 cp. Book marks moves in the bundled common opening lines. Brilliant marks a best move that offers a capturable non-pawn piece without meaningful evaluation loss; Great marks a best move with a large gap over the engine's second choice. Miss marks a 1–3 pawn loss from a position where the mover was already winning. These additional labels are heuristics, not official chess ratings. The summary accuracy is a simple heuristic (`100 - average centipawn loss / 10`, clamped to 0–100).

## Current scope

Profile editing, Chess.com connection and sync controls are available from the app navigation. SQLite remains the local default; PostgreSQL and Redis are provided by Docker Compose for multi-service deployment.
