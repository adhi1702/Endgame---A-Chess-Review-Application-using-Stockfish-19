"""Add profile, authentication, Chess.com and analysis metadata tables.

The original 0001 migration creates tables from current metadata. This
revision therefore skips objects that already exist, while upgrading
databases where 0001 was previously applied.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

from app.db import Base
from app import models  # noqa: F401

revision = "304a213ab6b9"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def _inspector():
    return inspect(op.get_bind())


def upgrade():
    bind = op.get_bind()
    # Create newly introduced tables and their indexes/constraints. Existing
    # tables are left intact and are amended below.
    Base.metadata.create_all(bind)
    inspector = _inspector()

    added_columns = {
        "users": ("display_name", "profile_picture", "country", "bio", "is_active"),
        "games": (
            "connected_account_id", "external_game_id", "white_rating",
            "black_rating", "user_color", "opening_name", "eco_code",
            "time_control",
        ),
        "analysis_jobs": (
            "engine_name", "engine_version", "engine_config", "total_moves",
            "analysis_status", "white_cpl", "black_cpl",
        ),
        "game_analyses": ("white_cpl", "black_cpl"),
        "move_analyses": (
            "ply", "move_number", "color", "played_move", "mate_before", "mate_after",
        ),
        "user_sessions": ("csrf_token_hash",),
    }
    existing_tables = set(inspector.get_table_names())
    for table_name, names in added_columns.items():
        if table_name not in existing_tables:
            continue
        existing = {column["name"] for column in inspector.get_columns(table_name)}
        table = Base.metadata.tables[table_name]
        missing = [name for name in names if name not in existing]
        if missing or (table_name == "users" and not _column_nullable(inspector, "users", "password_hash")):
            with op.batch_alter_table(table_name) as batch:
                for name in missing:
                    batch.add_column(table.c[name].copy())
                if table_name == "users" and not _column_nullable(inspector, "users", "password_hash"):
                    batch.alter_column("password_hash", existing_type=sa.String(255), nullable=True)

    inspector = _inspector()
    if "games" in inspector.get_table_names() and "imported_at" not in {column["name"] for column in inspector.get_columns("games")}:
        op.add_column("games", sa.Column("imported_at", sa.DateTime(timezone=True), nullable=True))
        op.execute(sa.text("UPDATE games SET imported_at = CURRENT_TIMESTAMP WHERE imported_at IS NULL"))
        with op.batch_alter_table("games") as batch:
            batch.alter_column("imported_at", existing_type=sa.DateTime(timezone=True), nullable=False)

    # Give existing users a usable profile name without associating Google
    # identities by email. Identity linking is an explicit password-verified flow.
    if "users" in _inspector().get_table_names():
        op.execute(sa.text("UPDATE users SET display_name = username WHERE display_name = 'Player'"))
    if "analysis_jobs" in _inspector().get_table_names():
        op.execute(sa.text("UPDATE analysis_jobs SET analysis_status = status"))

    # Add indexes and game constraints that create_all cannot add to a table
    # that existed before this revision.
    inspector = _inspector()
    if "games" in inspector.get_table_names():
        game_constraints = {c.get("name") for c in inspector.get_unique_constraints("games")}
        game_fks = {fk.get("name") for fk in inspector.get_foreign_keys("games")}
        with op.batch_alter_table("games") as batch:
            if "uq_game_connected_external" not in game_constraints:
                batch.create_unique_constraint("uq_game_connected_external", ["connected_account_id", "external_game_id"])
            if "fk_games_connected_account_id" not in game_fks:
                batch.create_foreign_key("fk_games_connected_account_id", "connected_accounts", ["connected_account_id"], ["id"], ondelete="SET NULL")
        inspector = _inspector()
        indexes = {idx["name"] for idx in inspector.get_indexes("games")}
        for index in Base.metadata.tables["games"].indexes:
            if index.name not in indexes:
                op.create_index(index.name, "games", [column.name for column in index.columns], unique=index.unique)
    # Also ensure unique indexes on newly-created tables in databases where
    # Base.metadata.create_all skipped a pre-existing version of that table.
    inspector = _inspector()
    for table_name in ("connected_accounts", "auth_accounts", "account_link_challenges", "user_sessions", "user_preferences"):
        if table_name not in inspector.get_table_names(): continue
        existing_unique = {item.get("name") for item in inspector.get_unique_constraints(table_name)}
        expected = [item for item in Base.metadata.tables[table_name].constraints if isinstance(item, sa.UniqueConstraint) and item.name]
        for constraint in expected:
            if constraint.name not in existing_unique:
                with op.batch_alter_table(table_name) as batch:
                    batch.create_unique_constraint(constraint.name, [column.name for column in constraint.columns])


def _column_nullable(inspector, table_name, column_name):
    return next(c["nullable"] for c in inspector.get_columns(table_name) if c["name"] == column_name)


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    for table_name in ("sync_jobs", "account_link_challenges", "user_sessions", "chess_ratings", "user_preferences", "auth_accounts"):
        if table_name in inspector.get_table_names():
            op.drop_table(table_name)
    if "games" in inspector.get_table_names():
        constraints = {item.get("name") for item in inspector.get_unique_constraints("games")}
        foreign_keys = {item.get("name") for item in inspector.get_foreign_keys("games")}
        indexes = {item.get("name") for item in inspector.get_indexes("games")}
        with op.batch_alter_table("games") as batch:
            if "uq_game_connected_external" in constraints: batch.drop_constraint("uq_game_connected_external", type_="unique")
            if "fk_games_connected_account_id" in foreign_keys: batch.drop_constraint("fk_games_connected_account_id", type_="foreignkey")
            for name in ("ix_games_connected_account_id", "ix_games_user_played"):
                if name in indexes: batch.drop_index(name)
            for name in ("connected_account_id", "external_game_id", "white_rating", "black_rating", "user_color", "opening_name", "eco_code", "time_control", "imported_at"):
                if name in {c["name"] for c in inspector.get_columns("games")}: batch.drop_column(name)
    for table_name, names in {
        "users": ("display_name", "profile_picture", "country", "bio", "is_active"),
        "analysis_jobs": ("engine_name", "engine_version", "engine_config", "total_moves", "analysis_status", "white_cpl", "black_cpl"),
        "game_analyses": ("white_cpl", "black_cpl"),
        "move_analyses": ("ply", "move_number", "color", "played_move", "mate_before", "mate_after"),
        "user_sessions": ("csrf_token_hash",),
    }.items():
        if table_name not in inspect(bind).get_table_names(): continue
        existing = {c["name"] for c in inspect(bind).get_columns(table_name)}
        to_drop = [name for name in names if name in existing]
        if to_drop:
            with op.batch_alter_table(table_name) as batch:
                for name in to_drop: batch.drop_column(name)
    if "password_hash" in {c["name"] for c in inspect(bind).get_columns("users")} and _column_nullable(inspect(bind), "users", "password_hash"):
        with op.batch_alter_table("users") as batch:
            batch.alter_column("password_hash", existing_type=sa.String(255), nullable=False)
