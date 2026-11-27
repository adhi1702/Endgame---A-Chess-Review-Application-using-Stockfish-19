# Stockfish Review --- Implementation Plan

**Project:** Stockfish Review\
**Document:** Product and Technical Implementation Plan\
**Version:** 1.0\
**Date:** 27 November 2026

------------------------------------------------------------------------

## 1. Project Overview

Stockfish Review is a multi-user chess game review application. Users
sign in with Google, connect a public Chess.com username, import their
games, review games with Stockfish 19, and track their chess performance
over time.

The implementation must extend the existing project rather than replace
its structure.

### Version 1.0 goals

1.  Google sign-in and secure application sessions.
2.  User profile and preferences.
3.  Chess.com account linking through its Published-Data API.
4.  Manual and scheduled game synchronization.
5.  Game history and PGN storage.
6.  Stockfish 19 game analysis.
7.  Move classifications and game-level review summaries.
8.  Chess performance analytics.

### Out of scope for the first release

-   Chess.com OAuth or actions on behalf of a Chess.com user.
-   Other chess-platform integrations.
-   Social features, friends, messaging or leaderboards.
-   Mobile applications.
-   Microservices.
-   AI-generated coaching reports. These can be considered after
    reliable game analytics exist.

------------------------------------------------------------------------

## 2. Existing Project Structure

The current repository is:

``` text
Stockfish_Review/
├── backend/
│   ├── app/
│   │   ├── core/
│   │   │   └── config.py
│   │   ├── engine/
│   │   │   └── stockfish.py
│   │   ├── services/
│   │   │   ├── classification.py
│   │   │   ├── opening_book.py
│   │   │   └── pgn.py
│   │   ├── db.py
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   └── worker.py
│   ├── migrations/
│   │   ├── versions/
│   │   │   └── 0001_initial.py
│   │   ├── env.py
│   │   └── script.py.mako
│   ├── alembic.ini
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api.ts
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   ├── style.css
│   │   └── vite-env.d.ts
│   ├── index.html
│   ├── package.json
│   ├── package-lock.json
│   ├── postcss.config.js
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   └── vite.config.ts
├── docker-compose.yml
└── README.md
```

### Structure-preservation rules

-   Keep the existing React + Vite frontend.
-   Keep FastAPI as the backend.
-   Extend `models.py`, `schemas.py`, `db.py` and `main.py` rather than
    replacing them.
-   Preserve and reuse the existing Stockfish integration in
    `engine/stockfish.py`.
-   Preserve and reuse existing PGN parsing, opening-book and
    classification functionality.
-   Inspect the existing implementation before changing any function,
    schema or migration.
-   Do not delete or rewrite working functionality merely to match a
    proposed folder layout.
-   Add modules incrementally when a file becomes too large or a
    responsibility needs isolation.

### Suggested incremental additions

``` text
backend/app/
├── api/
│   └── v1/
│       ├── auth.py
│       ├── users.py
│       ├── integrations.py
│       ├── games.py
│       ├── reviews.py
│       └── analytics.py
├── core/
│   ├── config.py
│   ├── security.py
│   └── dependencies.py
├── services/
│   ├── classification.py
│   ├── opening_book.py
│   ├── pgn.py
│   ├── auth_service.py
│   ├── profile_service.py
│   ├── chesscom_service.py
│   ├── sync_service.py
│   ├── game_service.py
│   ├── review_service.py
│   └── analytics_service.py
├── engine/
│   └── stockfish.py
├── tasks/
│   ├── sync_tasks.py
│   └── analysis_tasks.py
├── db.py
├── models.py
├── schemas.py
├── worker.py
└── main.py

frontend/src/
├── components/
│   ├── common/
│   ├── layout/
│   ├── charts/
│   └── chessboard/
├── features/
│   ├── authentication/
│   ├── profile/
│   ├── chesscom/
│   ├── games/
│   └── analytics/
├── pages/
│   ├── Login/
│   ├── Dashboard/
│   ├── Profile/
│   ├── GameHistory/
│   ├── GameReview/
│   ├── Analytics/
│   └── Settings/
├── hooks/
├── services/
├── types/
├── utils/
├── api.ts
├── App.tsx
└── main.tsx
```

These are additions, not a mandatory one-time restructure. Keep the
current file layout if the codebase is still small and coherent.

------------------------------------------------------------------------

## 3. Technology Decisions

  -----------------------------------------------------------------------
  Layer                   Technology              Purpose
  ----------------------- ----------------------- -----------------------
  Frontend                React + TypeScript +    User interface
                          Vite                    

  Styling                 Existing Tailwind CSS   UI styling
                          setup                   

  Charts                  Recharts or existing    Analytics
                          chart library           visualizations

  Backend                 FastAPI                 REST API

  Database                PostgreSQL              Persistent application
                                                  data

  ORM                     Existing SQLAlchemy     Database access
                          setup / SQLAlchemy 2.x  

  Migrations              Existing Alembic setup  Schema evolution

  Authentication          Google Identity         Google sign-in
                          Services                

  Session                 Opaque server-side      Application
                          session in secure       authentication
                          cookie                  

  Chess parsing           python-chess            PGN parsing and legal
                                                  position handling

  Engine                  Pinned Stockfish 19     Position analysis
                          binary and NNUE files   

  Queue                   Celery                  Background work

  Broker                  Redis                   Task queue and
                                                  coordination

  Scheduler               Celery Beat             Scheduled
                                                  synchronization
  -----------------------------------------------------------------------

Use the versions already installed where possible. Upgrade dependencies
deliberately and test after each upgrade.

------------------------------------------------------------------------

## 4. Architecture

Use a modular monolith for Version 1.0.

-   React communicates with FastAPI over versioned HTTP APIs.
-   FastAPI authenticates users and enforces ownership checks.
-   PostgreSQL is the source of truth for users, connected accounts,
    games and analysis.
-   Chess.com integration retrieves public player and game data.
-   Celery workers handle synchronization and engine analysis.
-   Redis brokers background tasks.
-   Stockfish runs as a separate process controlled through UCI.
-   The frontend never connects directly to PostgreSQL, Redis, Chess.com
    or the Stockfish executable.

Keep game import and game analysis as separate workflows. A game may be
imported without being analyzed.

------------------------------------------------------------------------

## 5. Database Plan

Inspect the existing initial migration and current models before
creating or modifying tables. Use Alembic migrations for every schema
change. Do not edit an already-applied migration in a shared or
persistent database; create a new migration instead.

Use UUID primary keys where appropriate, timezone-aware timestamps,
foreign keys, indexes and database constraints.

### 5.1 `users`

Stores the application's user profile.

  Column            Type           Notes
  ----------------- -------------- ----------------------------
  id                UUID           Primary key
  display_name      VARCHAR(100)   Required
  email             VARCHAR(255)   Required; normalized
  profile_picture   TEXT           Optional Google avatar URL
  country           VARCHAR(100)   Optional
  bio               TEXT           Optional
  is_active         BOOLEAN        Default true
  created_at        TIMESTAMPTZ    Creation time
  updated_at        TIMESTAMPTZ    Last update

Email is profile/contact information, not the stable Google identity
key.

### 5.2 `auth_accounts`

Stores external authentication identities.

  Column             Type           Notes
  ------------------ -------------- -------------------------
  id                 UUID           Primary key
  user_id            UUID           FK to users
  provider           VARCHAR(30)    `google` initially
  provider_user_id   VARCHAR(255)   Google's verified `sub`
  provider_email     VARCHAR(255)   Optional
  created_at         TIMESTAMPTZ    Creation time

Constraint: `UNIQUE(provider, provider_user_id)`.

### 5.3 `connected_accounts`

Stores linked chess-platform accounts.

  Column               Type           Notes
  -------------------- -------------- ------------------------
  id                   UUID           Primary key
  user_id              UUID           FK to users
  provider             VARCHAR(30)    `chesscom` initially
  external_username    VARCHAR(100)   Chess.com username
  external_player_id   VARCHAR(100)   If available
  profile_url          TEXT           Public profile URL
  avatar_url           TEXT           Optional
  connection_status    VARCHAR(30)    Active or disconnected
  sync_enabled         BOOLEAN        Default true
  connected_at         TIMESTAMPTZ    Connection time
  last_synced_at       TIMESTAMPTZ    Last successful sync

For Version 1.0, enforce one Chess.com account per application user with
`UNIQUE(user_id, provider)`. Do not claim username validation proves
ownership; it only confirms that the public profile exists.

### 5.4 `chess_ratings`

Stores rating snapshots.

  Column                 Type          Notes
  ---------------------- ------------- -----------------------------
  id                     UUID          Primary key
  user_id                UUID          FK to users
  connected_account_id   UUID          FK to connected_accounts
  game_type              VARCHAR(20)   Rapid, blitz, bullet, daily
  rating                 INTEGER       Rating value
  recorded_at            TIMESTAMPTZ   Snapshot time
  source                 VARCHAR(30)   Chess.com or imported game

Do not assume the Chess.com statistics endpoint provides a complete
historical rating series. Build a history from snapshots collected over
time and ratings present in imported games.

### 5.5 `games`

Stores imported and manually added games.

  Column                 Type           Notes
  ---------------------- -------------- ------------------------------------
  id                     UUID           Primary key
  user_id                UUID           FK to users
  connected_account_id   UUID           Nullable FK
  external_game_id       VARCHAR(255)   Nullable Chess.com game identifier
  source                 VARCHAR(30)    Chess.com or manual
  white_player           VARCHAR(100)   White player
  black_player           VARCHAR(100)   Black player
  white_rating           INTEGER        Optional
  black_rating           INTEGER        Optional
  user_color             VARCHAR(10)    White or black when known
  result                 VARCHAR(10)    PGN result
  opening_name           VARCHAR(255)   Optional
  eco_code               VARCHAR(10)    Optional
  time_control           VARCHAR(50)    Optional
  played_at              TIMESTAMPTZ    Optional
  pgn                    TEXT           Original PGN
  imported_at            TIMESTAMPTZ    Import time

Add a uniqueness constraint on
`(connected_account_id, external_game_id)` for external games. Ensure
manual games with NULL external identifiers remain supported. Add
indexes for `(user_id, played_at DESC)` and commonly used filters.

### 5.6 `game_analyses`

Stores one analysis run for a game.

  -----------------------------------------------------------------------
  Column                  Type                    Notes
  ----------------------- ----------------------- -----------------------
  id                      UUID                    Primary key

  game_id                 UUID                    FK to games

  engine_name             VARCHAR(50)             Stockfish

  engine_version          VARCHAR(30)             Pinned version

  engine_config           JSONB                   Depth, MultiPV, hash
                                                  and other settings

  analysis_depth          INTEGER                 Requested depth

  total_moves             INTEGER                 Analyzed plies or
                                                  moves; define
                                                  consistently

  white_accuracy          NUMERIC(5,2)            Application-defined
                                                  metric

  black_accuracy          NUMERIC(5,2)            Application-defined
                                                  metric

  white_cpl               NUMERIC(10,2)           Average CPL

  black_cpl               NUMERIC(10,2)           Average CPL

  analysis_status         VARCHAR(30)             Queued, running,
                                                  completed, failed,
                                                  cancelled

  started_at              TIMESTAMPTZ             Optional

  completed_at            TIMESTAMPTZ             Optional
  -----------------------------------------------------------------------

Allow multiple analysis runs for a game so that a game can be
re-analyzed using different engine settings or versions.

### 5.7 `move_analyses`

Stores per-ply engine output.

  Column              Type            Notes
  ------------------- --------------- ---------------------------------
  id                  UUID            Primary key
  analysis_id         UUID            FK to game_analyses
  ply                 INTEGER         Half-move index
  move_number         INTEGER         Full move number
  color               VARCHAR(10)     Side that played
  played_move         VARCHAR(10)     UCI move
  best_move           VARCHAR(10)     UCI best move, if available
  evaluation_before   NUMERIC(12,4)   Normalized evaluation
  evaluation_after    NUMERIC(12,4)   Normalized evaluation
  centipawn_loss      NUMERIC(12,4)   Non-negative loss where defined
  mate_before         INTEGER         Nullable mate score
  mate_after          INTEGER         Nullable mate score
  classification      VARCHAR(30)     Application classification
  best_line           TEXT            Principal variation

Constraint: `UNIQUE(analysis_id, ply)`. Store evaluation perspective
consistently, preferably White's perspective. Handle mate scores
separately rather than treating them as ordinary centipawn values.

### 5.8 `sync_jobs`

Tracks manual and scheduled synchronization.

  Column                 Type          Notes
  ---------------------- ------------- -----------------------------------------
  id                     UUID          Primary key
  user_id                UUID          FK to users
  connected_account_id   UUID          FK to connected_accounts
  sync_type              VARCHAR(30)   Initial, incremental, manual, scheduled
  status                 VARCHAR(30)   Queued, running, completed, failed
  games_found            INTEGER       Default 0
  games_imported         INTEGER       Default 0
  games_skipped          INTEGER       Default 0
  error_message          TEXT          Sanitized error
  started_at             TIMESTAMPTZ   Optional
  completed_at           TIMESTAMPTZ   Optional

### 5.9 `user_preferences`

Stores per-user display and analysis preferences.

  Column                   Type          Notes
  ------------------------ ------------- --------------------
  id                       UUID          Primary key
  user_id                  UUID          Unique FK to users
  board_theme              VARCHAR(50)   Board theme
  piece_theme              VARCHAR(50)   Piece theme
  default_analysis_depth   INTEGER       Validated range
  multipv                  INTEGER       Validated range
  auto_analyze             BOOLEAN       Default false
  auto_sync                BOOLEAN       Default true
  created_at               TIMESTAMPTZ   Creation time
  updated_at               TIMESTAMPTZ   Update time

### 5.10 `user_sessions`

Stores revocable application sessions.

  Column               Type          Notes
  -------------------- ------------- ------------------------------
  id                   UUID          Primary key
  user_id              UUID          FK to users
  session_token_hash   TEXT          Unique hash, never raw token
  expires_at           TIMESTAMPTZ   Expiration
  created_at           TIMESTAMPTZ   Creation time
  revoked_at           TIMESTAMPTZ   Nullable

### Database implementation rules

-   Every user-owned query must be scoped to the authenticated user's
    ID.
-   Add indexes for foreign keys and common filters.
-   Use transactions for account creation and game import batches.
-   Use database constraints as a second line of duplicate protection.
-   Store original PGNs so games can be re-analyzed without downloading
    them again.
-   Do not store Google ID tokens as long-lived application credentials.
-   Consider materialized views or cached aggregates only after
    measuring analytics query performance.

------------------------------------------------------------------------

## 6. Authentication and Session Flow

Google is the only login provider for Version 1.0.

### Login flow

1.  React displays the Google sign-in control.
2.  Google Identity Services returns an ID token.
3.  React sends the token to `POST /api/v1/auth/google`.
4.  FastAPI verifies the token's signature, issuer, audience and
    expiration using Google's supported verification library.
5.  FastAPI reads the verified `sub` claim.
6.  The backend finds or creates the corresponding `auth_accounts`
    record.
7.  For a new account, create the `users` and `user_preferences` records
    in a single transaction.
8.  Generate a cryptographically random opaque session token.
9.  Store only its hash in `user_sessions`.
10. Set the raw token in a Secure, HttpOnly, SameSite cookie.
11. Return a minimal user profile to React.

### Required authentication endpoints

  Method   Endpoint                    Purpose
  -------- --------------------------- ------------------------------------
  POST     `/api/v1/auth/google`       Verify Google ID token and sign in
  GET      `/api/v1/auth/me`           Return current user
  POST     `/api/v1/auth/logout`       Revoke current session
  POST     `/api/v1/auth/logout-all`   Revoke all user sessions

### Session rules

-   Use HTTPS in production.
-   Use `HttpOnly`, `Secure` and an appropriate `SameSite` cookie
    policy.
-   Protect cookie-authenticated state-changing requests against CSRF.
-   Validate allowed frontend origins.
-   Rotate or renew sessions according to the chosen expiry policy.
-   Revoke sessions on logout and account deletion.
-   Do not merge accounts solely because email addresses match.
-   Use the verified Google `sub` as the stable provider identity.

------------------------------------------------------------------------

## 7. Chess.com Integration

Use the Chess.com Published-Data API for public profile, statistics,
archives and game data. This integration is read-only and does not
require a Chess.com OAuth login for public games.

### API resources

``` text
GET https://api.chess.com/pub/player/{username}
GET https://api.chess.com/pub/player/{username}/stats
GET https://api.chess.com/pub/player/{username}/games/archives
GET https://api.chess.com/pub/player/{username}/games/{YYYY}/{MM}
GET https://api.chess.com/pub/player/{username}/games/{YYYY}/{MM}/pgn
```

Confirm current endpoint response formats and API requirements against
the official documentation while implementing. Use a descriptive
User-Agent header. Respect response caching and rate limits; do not
issue parallel requests aggressively.

### Connect flow

1.  Authenticated user submits a Chess.com username.
2.  Backend validates and normalizes the username.
3.  Backend requests the public player profile.
4.  If the profile exists, save a `connected_accounts` record.
5.  Return the public profile information and connection status.
6.  Offer an initial import.

The UI must explain that this verifies the existence of a public
profile, not ownership of the Chess.com account.

### Synchronization policy

-   First connection: import the most recent three months by default.
-   Offer historical backfill separately.
-   Manual sync: user starts an incremental sync.
-   Scheduled sync: run every 12--24 hours.
-   Store imported games and skip known external game identifiers.
-   Fetch only the necessary archive months.
-   Respect API caching and rate-limit responses.
-   Retry transient failures with exponential backoff and jitter.
-   Do not retry permanent invalid-username or malformed-data errors
    indefinitely.
-   Prevent multiple concurrent sync jobs for the same connected
    account.
-   Stop scheduled sync when the user disconnects the account or
    disables synchronization.

Do not assume every newly played game will be immediately available
through the Published-Data API.

### Required Chess.com endpoints

  -------------------------------------------------------------------------------------------------------
  Method                  Endpoint                                                Purpose
  ----------------------- ------------------------------------------------------- -----------------------
  POST                    `/api/v1/integrations/chesscom/connect`                 Validate and connect
                                                                                  username

  GET                     `/api/v1/integrations/chesscom/status`                  Connection and sync
                                                                                  status

  POST                    `/api/v1/integrations/chesscom/sync`                    Start manual sync

  GET                     `/api/v1/integrations/chesscom/sync-history`            List sync jobs

  GET                     `/api/v1/integrations/chesscom/sync-history/{job_id}`   Get job status

  DELETE                  `/api/v1/integrations/chesscom/disconnect`              Disable and remove
                                                                                  connection
  -------------------------------------------------------------------------------------------------------

Example connect request:

``` json
{
  "username": "chesscom_username"
}
```

Example sync request:

``` json
{
  "sync_mode": "incremental"
}
```

Return `202 Accepted` for queued background work:

``` json
{
  "job_id": "uuid",
  "status": "queued"
}
```

------------------------------------------------------------------------

## 8. Game Management

### Required endpoints

  Method   Endpoint                        Purpose
  -------- ------------------------------- -----------------------
  GET      `/api/v1/games`                 List user's games
  GET      `/api/v1/games/{game_id}`       Get game details
  POST     `/api/v1/games/import`          Import a PGN
  GET      `/api/v1/games/{game_id}/pgn`   Download original PGN
  DELETE   `/api/v1/games/{game_id}`       Delete a user's game

### Game list filters

Support pagination and optional filters:

``` text
GET /api/v1/games
    ?page=1
    &limit=20
    &result=win
    &color=white
    &time_control=rapid
    &review_status=completed
    &from_date=2026-11-01
    &to_date=2026-11-27
```

The backend must validate filter values and enforce a maximum page size.

### Import validation

-   Validate PGN size and encoding.
-   Parse the PGN using python-chess.
-   Validate the move sequence.
-   Handle missing or incomplete PGN headers.
-   Extract players, result, date, time control, opening metadata and
    ratings when present.
-   Preserve the original PGN.
-   Associate the game with the authenticated user.
-   Apply duplicate detection for external games.
-   Return useful validation errors without exposing internal
    exceptions.

------------------------------------------------------------------------

## 9. Stockfish 19 Review Pipeline

Reuse the existing `backend/app/engine/stockfish.py` and the current
review functionality. First inspect how the current engine is launched,
configured and closed.

### Analysis flow

1.  User selects an imported or manually added game.
2.  Backend verifies ownership.
3.  Backend validates the requested engine configuration.
4.  Create a `game_analyses` record with status `queued`.
5.  Enqueue an analysis task.
6.  Worker loads and validates the PGN.
7.  Worker initializes the pinned Stockfish 19 executable through UCI.
8.  Replay the game and analyze positions.
9.  Capture evaluation, best move, principal variation and engine
    metadata.
10. Calculate move losses and classifications.
11. Save move analysis records in batches or a transaction.
12. Calculate game-level summaries.
13. Mark the analysis completed.
14. On failure, record a sanitized error and mark the task failed.

### Initial engine configuration

  Setting         Initial value
  --------------- -----------------------------------------
  Engine          Stockfish 19
  Default depth   16
  MultiPV         3
  Threads         1 per engine process initially
  Hash            Conservative, configurable memory limit
  Interface       UCI
  Analysis        Background worker

All settings must be validated server-side. Depth 16 is a starting
point, not a guarantee of a particular strength or runtime.

### Evaluation rules

-   Store evaluations from a consistent perspective, preferably White's
    perspective.
-   Convert scores correctly when comparing the two sides.
-   Handle mate scores separately from centipawn scores.
-   Handle forced moves and positions with only one legal move.
-   Define precisely whether evaluation is taken before or after the
    played move.
-   Use a documented centipawn-loss formula.
-   Keep classification rules separate from engine output.
-   Record engine version and configuration for every analysis run.

### Move classification

Reuse and review `services/classification.py`.

Initial classifications can include:

-   Brilliant
-   Great
-   Best
-   Excellent
-   Good
-   Inaccuracy
-   Mistake
-   Blunder
-   Forced

These are application-defined labels, not labels directly returned by
Stockfish. Implement a documented rule set and test it against known
positions. Avoid classifying a forced move as a mistake merely because
another move has a similar evaluation.

### Review endpoints

  --------------------------------------------------------------------------------------
  Method                  Endpoint                               Purpose
  ----------------------- -------------------------------------- -----------------------
  POST                    `/api/v1/games/{game_id}/review`       Queue analysis

  GET                     `/api/v1/games/{game_id}/review`       Get latest analysis

  GET                     `/api/v1/reviews/{review_id}`          Get analysis status and
                                                                 summary

  GET                     `/api/v1/reviews/{review_id}/moves`    Get move evaluations

  POST                    `/api/v1/reviews/{review_id}/cancel`   Request cancellation
  --------------------------------------------------------------------------------------

Return `202 Accepted` when analysis is queued. The frontend should poll
the status endpoint initially. Add Server-Sent Events only if live
progress becomes necessary.

------------------------------------------------------------------------

## 10. Background Jobs

Use Redis and Celery for long-running work.

### Queues

  Queue             Tasks
  ----------------- --------------------------------------------
  `chess_sync`      Chess.com profile and game synchronization
  `game_analysis`   Stockfish analysis
  `maintenance`     Cleanup and scheduled maintenance

### Job priorities

1.  User-requested game review: high priority.
2.  Routine incremental synchronization: normal priority.
3.  Historical backfill and bulk analysis: low priority.

### Worker requirements

-   Configure task timeouts and bounded retries.
-   Make tasks idempotent.
-   Prevent duplicate active sync jobs for an account.
-   Track task IDs alongside database job records.
-   Persist status and error information in PostgreSQL.
-   Ensure worker failures do not leave records permanently marked as
    running.
-   Limit concurrent Stockfish processes based on available CPU and
    memory.
-   Reuse engine processes safely where practical, but never share one
    UCI process concurrently across independent tasks without
    synchronization.
-   Close engine processes cleanly.

Redis is the broker, not the permanent record of job status. PostgreSQL
job records are authoritative.

------------------------------------------------------------------------

## 11. Analytics

Calculate analytics from imported games and completed analysis records.
Do not create a separate permanent analytics table in the first release
unless measured performance requires it.

### Overview metrics

-   Total imported games.
-   Total reviewed games.
-   Wins, draws and losses.
-   Win, draw and loss rates.
-   Average accuracy.
-   Average centipawn loss.
-   Blunders and mistakes.
-   Performance as White and Black.

### Additional analytics

-   Rating snapshots over time.
-   Opening frequency and results.
-   Performance by time control.
-   Accuracy trend.
-   Mistakes per game.
-   Performance as White versus Black.
-   Comparison of recent games with an earlier period.

### Metric definitions

-   Win rate: wins divided by decisive games.
-   Draw rate: draws divided by all games.
-   Loss rate: losses divided by decisive games.
-   Average CPL: average eligible centipawn loss for the selected side.
-   Blunders per game: blunders divided by reviewed games.

Document every metric. Do not mix official Chess.com statistics with
application-derived engine statistics. Do not compare analyses with
different engine configurations or depths as if they were directly
equivalent.

### Analytics endpoints

  Method   Endpoint
  -------- ---------------------------------------
  GET      `/api/v1/analytics/overview`
  GET      `/api/v1/analytics/ratings`
  GET      `/api/v1/analytics/openings`
  GET      `/api/v1/analytics/performance`
  GET      `/api/v1/analytics/mistakes`
  GET      `/api/v1/analytics/color-performance`

Support a common date-range filter, such as `7d`, `30d`, `90d` and
`all`.

------------------------------------------------------------------------

## 12. Frontend Plan

Use the existing React + Vite + TypeScript application.

### Navigation

1.  Dashboard
2.  Game Review
3.  Game History
4.  Analytics
5.  Profile
6.  Settings

### Pages

#### Login

-   Application branding.
-   Continue with Google.
-   Loading and error states.
-   Redirect authenticated users to the dashboard.

#### Dashboard

-   Chess.com connection status.
-   Latest rating snapshots.
-   Recent imported games.
-   Recent review activity.
-   Synchronization status.
-   Basic performance overview.

#### Profile

Use tabs:

1.  Overview
2.  Statistics
3.  Game History
4.  Connected Accounts
5.  Settings

Profile fields:

-   Profile picture.
-   Display name.
-   Email.
-   Country and optional bio.
-   Account creation date.
-   Chess.com username and connection status.
-   Imported and reviewed game counts.
-   Selected chess statistics.

#### Game History

-   Paginated list.
-   Date and time-control filters.
-   White/Black filter.
-   Win/draw/loss filter.
-   Review status.
-   Open review action.
-   Original PGN access.

#### Game Review

Reuse the existing chessboard and review components.

-   Interactive chessboard.
-   Move list and navigation.
-   Evaluation graph.
-   Best move and principal variation.
-   Move classifications.
-   Engine analysis settings.
-   Review status.

#### Analytics

-   Rating progression.
-   Win/draw/loss chart.
-   Accuracy trend.
-   Opening performance.
-   Blunder and mistake distribution.
-   White versus Black comparison.

#### Settings

-   Board and piece themes.
-   Default analysis depth and MultiPV.
-   Automatic analysis preference.
-   Automatic synchronization preference.
-   Connected account management.
-   Logout and account deletion.

### Frontend data handling

-   Use the existing API client in `frontend/src/api.ts`.
-   Add a consistent API error-handling strategy.
-   Use TanStack Query if a server-state library is needed.
-   Keep authentication state minimal.
-   Do not store session credentials in localStorage.
-   Keep game and analytics data in server-state caches, not a large
    global context.
-   Ensure every page has loading, empty, error and success states.

------------------------------------------------------------------------

## 13. Security Requirements

Security is a release requirement, not a later enhancement.

### Authentication

-   Verify Google ID tokens on the backend.
-   Validate signature, issuer, audience and expiry.
-   Use verified Google `sub` as the provider identifier.
-   Never trust an email or user ID sent by React as authentication
    proof.
-   Use random opaque session tokens and store only token hashes.
-   Use secure cookies and CSRF protection.

### Authorization

-   Derive the user ID from the authenticated session.
-   Scope every game, analysis, sync job and profile query to that user.
-   Check ownership before retrieving, modifying or deleting a resource.
-   Test cross-user access explicitly.

### API and input security

-   Configure strict CORS origins.
-   Validate request bodies and query parameters.
-   Limit PGN upload size and analysis settings.
-   Rate-limit authentication, sync and analysis endpoints.
-   Avoid arbitrary URL fetching.
-   Avoid exposing stack traces or internal secrets.
-   Use parameterized database operations through the ORM.

### Infrastructure

-   Keep PostgreSQL and Redis private.
-   Do not commit `.env` files or credentials.
-   Use environment variables for local development and a secret manager
    in production.
-   Use HTTPS in production.
-   Back up PostgreSQL.
-   Avoid logging Google tokens, cookies, session IDs or sensitive
    request headers.

### Stockfish worker

-   Use a fixed trusted executable path.
-   Do not accept executable paths or arbitrary UCI commands from users.
-   Restrict CPU, memory and task duration.
-   Validate PGNs before analysis.
-   Pin the Stockfish 19 binary and NNUE files.
-   Review GPL-3.0 obligations before distributing the engine with the
    application.

------------------------------------------------------------------------

## 14. Implementation Phases

Implement the project in the following order. Each phase should have a
working, testable deliverable before the next phase begins.

### Phase 0 --- Inspect and stabilize the existing application

Tasks:

-   Inspect the existing FastAPI routes and current request/response
    contracts.
-   Inspect `models.py`, `schemas.py`, `db.py` and the initial Alembic
    migration.
-   Inspect the existing Stockfish engine wrapper.
-   Inspect PGN parsing, opening-book and classification services.
-   Inspect the React application and current API client.
-   Verify PostgreSQL connection and existing Docker Compose services.
-   Run existing tests and record current behavior.
-   Identify functionality that must not regress.

Deliverable: A written map of existing functionality, identified gaps
and a baseline test result.

### Phase 1 --- Database and backend foundation

Tasks:

-   Confirm PostgreSQL configuration.
-   Add the required SQLAlchemy models.
-   Create Alembic migrations.
-   Add indexes and unique constraints.
-   Add common API dependencies.
-   Configure application settings.
-   Add health-check and database readiness endpoints.
-   Add test fixtures and database tests.

Deliverable: Migrated database and stable backend foundation.

### Phase 2 --- Google authentication and user profile

Tasks:

-   Configure Google Identity Services.
-   Implement Google ID token verification.
-   Implement `auth_accounts` and user creation.
-   Implement secure session creation and revocation.
-   Implement current-user dependency.
-   Add profile and preference endpoints.
-   Add protected React routes.
-   Build login, logout, profile and settings screens.

Deliverable: A user can sign in with Google and access a persistent
personal profile.

### Phase 3 --- Chess.com connection and initial import

Tasks:

-   Implement the Chess.com API client.
-   Validate public usernames.
-   Save connected account information.
-   Fetch public player statistics.
-   Fetch game archive URLs.
-   Retrieve recent game data and PGNs.
-   Parse and validate PGNs.
-   Save games with source and external identifiers.
-   Implement duplicate detection.
-   Build the connected-account and game-history UI.

Deliverable: A signed-in user can connect Chess.com and import recent
games.

### Phase 4 --- Manual and scheduled synchronization

Tasks:

-   Add Redis and Celery.
-   Configure separate task queues.
-   Implement manual sync jobs.
-   Implement scheduled incremental synchronization.
-   Add retry and rate-limit handling.
-   Prevent concurrent account syncs.
-   Track sync status in PostgreSQL.
-   Build sync history and progress UI.
-   Implement disconnect and scheduled-job cancellation behavior.

Deliverable: Users can manually synchronize games and receive scheduled
updates.

### Phase 5 --- Stockfish review integration

Tasks:

-   Preserve and extend the existing UCI engine wrapper.
-   Pin the Stockfish 19 executable and NNUE files.
-   Add analysis job records.
-   Queue analysis tasks.
-   Parse PGNs and replay moves.
-   Capture position evaluations and principal variations.
-   Calculate centipawn loss.
-   Implement and test move classification.
-   Save move-by-move and game-level analysis.
-   Add analysis status endpoints.

Deliverable: A user can request and retrieve Stockfish 19 analysis for
an imported game.

### Phase 6 --- Review interface

Tasks:

-   Reuse the existing chessboard.
-   Connect the board to saved PGN and move analysis.
-   Display move classifications.
-   Display engine evaluation and best lines.
-   Add move navigation and position synchronization.
-   Add evaluation graph.
-   Add analysis progress and failure states.
-   Allow users to revisit completed reviews.

Deliverable: A complete review workflow for imported games.

### Phase 7 --- Analytics and dashboard

Tasks:

-   Implement analytics service queries.
-   Define and test statistical formulas.
-   Add rating snapshots.
-   Implement opening statistics.
-   Implement color-based performance.
-   Implement accuracy and CPL trends.
-   Build dashboard cards and charts.
-   Add common date-range filters.

Deliverable: A personal chess performance dashboard based on actual
stored data.

### Phase 8 --- Hardening and release

Tasks:

-   Run authentication and authorization tests.
-   Run cross-user data isolation tests.
-   Test Chess.com API failures and rate limits.
-   Test duplicate and partial imports.
-   Test invalid PGNs and special chess positions.
-   Test Stockfish worker crashes and retries.
-   Test analysis consistency.
-   Test analytics calculations.
-   Add database backup and recovery procedure.
-   Configure production secrets and HTTPS.
-   Add structured logging and health monitoring.
-   Review Stockfish licensing obligations.
-   Update README with setup, migrations, environment variables and
    deployment instructions.

Deliverable: Version 1.0 release candidate.

------------------------------------------------------------------------

## 15. Testing Plan

  -----------------------------------------------------------------------
  Area                                Required test cases
  ----------------------------------- -----------------------------------
  Google authentication               Valid token, invalid token, expired
                                      token, first login, repeat login

  Sessions                            Cookie flags, expiration, logout,
                                      revocation

  Profiles                            Read, update, invalid fields

  Authorization                       User A cannot access User B's
                                      resources

  Chess.com                           Valid username, unknown username,
                                      timeout, malformed response

  Synchronization                     Initial import, incremental import,
                                      duplicate, retry, partial failure

  PGN                                 Valid game, invalid syntax, illegal
                                      move, incomplete headers

  Stockfish                           Normal position, checkmate, forced
                                      move, mate score, engine timeout

  Classification                      Known tactical and non-tactical
                                      test positions

  Analytics                           Win/loss/draw formulas, color
                                      split, CPL and opening aggregation

  Background jobs                     Retry, cancellation, duplicate task
                                      prevention, worker restart

  Frontend                            Loading, empty, error,
                                      authenticated and unauthenticated
                                      states
  -----------------------------------------------------------------------

Use deterministic test PGNs and fixed engine settings when comparing
analysis output. Engine output can differ when settings, binary, NNUE
files or hardware behavior differ.

------------------------------------------------------------------------

## 16. Local Development and Docker

Extend the existing `docker-compose.yml`; do not replace it blindly.

The intended services are:

  Service         Responsibility
  --------------- ----------------------------------------------
  frontend        React production build or development server
  backend         FastAPI
  postgres        PostgreSQL database
  redis           Celery broker
  celery_worker   Synchronization and analysis jobs
  celery_beat     Scheduled synchronization

The Stockfish binary and NNUE files must be available to the engine
worker. Prefer a pinned binary and documented setup process.

For local development on a resource-constrained machine:

-   Start with one Stockfish process.
-   Use one engine thread initially.
-   Set a conservative hash size.
-   Limit concurrent analysis tasks.
-   Avoid running multiple full-game analyses simultaneously.
-   Keep API and worker processes separate.

Add database readiness checks and persistent PostgreSQL volumes. Do not
use a production database password committed in Compose or source
control.

------------------------------------------------------------------------

## 17. API Contract Summary

All application endpoints use `/api/v1`.

### Authentication

  Method   Route
  -------- --------------------
  POST     `/auth/google`
  GET      `/auth/me`
  POST     `/auth/logout`
  POST     `/auth/logout-all`

### Users

  Method   Route
  -------- ----------------------
  GET      `/users/profile`
  PATCH    `/users/profile`
  GET      `/users/preferences`
  PATCH    `/users/preferences`

### Chess.com

  Method   Route
  -------- ------------------------------------------------
  POST     `/integrations/chesscom/connect`
  GET      `/integrations/chesscom/status`
  POST     `/integrations/chesscom/sync`
  GET      `/integrations/chesscom/sync-history`
  GET      `/integrations/chesscom/sync-history/{job_id}`
  DELETE   `/integrations/chesscom/disconnect`

### Games

  Method   Route
  -------- ------------------------
  GET      `/games`
  GET      `/games/{game_id}`
  POST     `/games/import`
  GET      `/games/{game_id}/pgn`
  DELETE   `/games/{game_id}`

### Reviews

  Method   Route
  -------- -------------------------------
  POST     `/games/{game_id}/review`
  GET      `/games/{game_id}/review`
  GET      `/reviews/{review_id}`
  GET      `/reviews/{review_id}/moves`
  POST     `/reviews/{review_id}/cancel`

### Analytics

  Method   Route
  -------- --------------------------------
  GET      `/analytics/overview`
  GET      `/analytics/ratings`
  GET      `/analytics/openings`
  GET      `/analytics/performance`
  GET      `/analytics/mistakes`
  GET      `/analytics/color-performance`

Use consistent error response schemas, HTTP status codes and pagination.
Return `202 Accepted` for background jobs rather than keeping the
request open until the job finishes.

------------------------------------------------------------------------

## 18. Version 1.0 Acceptance Checklist

The first release is complete when all of the following work:

-   [ ] User can sign in using Google.
-   [ ] User profile is persisted in PostgreSQL.
-   [ ] User can log out and revoke their session.
-   [ ] Protected pages require authentication.
-   [ ] User can connect a public Chess.com username.
-   [ ] Application imports recent Chess.com games.
-   [ ] Duplicate games are not imported.
-   [ ] User can manually synchronize games.
-   [ ] Scheduled synchronization works.
-   [ ] User can browse and filter imported games.
-   [ ] User can request Stockfish 19 analysis.
-   [ ] Move-by-move evaluations are saved.
-   [ ] User can reopen completed reviews.
-   [ ] Analytics are calculated from stored games and analysis.
-   [ ] Users cannot access another user's private records.
-   [ ] Background job failures are visible and recoverable.
-   [ ] Setup, migration and deployment instructions are documented.

------------------------------------------------------------------------

## 19. Official References

Use official documentation as the source of truth during implementation.

-   Google Identity Services:
    https://developers.google.com/identity/gsi/web
-   Google ID token verification:
    https://developers.google.com/identity/gsi/web/guides/verify-google-id-token
-   Chess.com Published-Data API:
    https://support.chess.com/en/articles/9650547-what-is-the-pubapi-and-how-do-i-use-it
-   Stockfish: https://stockfishchess.org/
-   Stockfish UCI documentation:
    https://official-stockfish.github.io/docs/stockfish-wiki/UCI-&-Commands.html
-   python-chess: https://python-chess.readthedocs.io/
-   FastAPI: https://fastapi.tiangolo.com/
-   SQLAlchemy: https://docs.sqlalchemy.org/en/20/
-   Alembic: https://alembic.sqlalchemy.org/
-   Celery: https://docs.celeryq.dev/
-   PostgreSQL: https://www.postgresql.org/docs/
-   Redis: https://redis.io/docs/

------------------------------------------------------------------------

## 20. Recommended Immediate Next Steps

Do not begin by restructuring the entire repository.

1.  Inspect the existing code and identify which profile, game, review
    and engine functionality already exists.
2.  Verify the current database models and initial migration.
3.  Add the user, authentication account, session, connected account and
    preference models.
4.  Create and test a new Alembic migration.
5.  Implement Google authentication and the current-user endpoint.
6.  Build the profile UI against the authenticated API.
7.  Only then begin Chess.com integration.

**Implementation rule:** Work phase by phase, preserve existing working
Stockfish functionality, write tests for each new module, and do not
mark a phase complete until its deliverables work end to end.
