"""Add source controls, persistent story curation, and app settings."""

import sqlalchemy as sa
from alembic import op

revision = "20261022_0003"
down_revision = "20260923_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    source_columns = {column["name"] for column in inspector.get_columns("sources")}
    if "is_active" not in source_columns:
        op.add_column("sources", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))

    inspector = sa.inspect(bind)
    story_columns = {column["name"] for column in inspector.get_columns("stories")}
    if "is_manually_curated" not in story_columns:
        op.add_column("stories", sa.Column("is_manually_curated", sa.Boolean(), nullable=False, server_default=sa.false()))

    if "app_settings" not in sa.inspect(bind).get_table_names():
        op.create_table(
            "app_settings",
            sa.Column("key", sa.String(length=80), primary_key=True),
            sa.Column("value", sa.JSON(), nullable=False),
        )


def downgrade() -> None:
    bind = op.get_bind()
    if "app_settings" in sa.inspect(bind).get_table_names():
        op.drop_table("app_settings")
    inspector = sa.inspect(bind)
    if "is_manually_curated" in {column["name"] for column in inspector.get_columns("stories")}:
        op.drop_column("stories", "is_manually_curated")
    inspector = sa.inspect(bind)
    if "is_active" in {column["name"] for column in inspector.get_columns("sources")}:
        op.drop_column("sources", "is_active")
