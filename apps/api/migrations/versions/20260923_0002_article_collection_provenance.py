"""Add provenance fields used by online research runs.

The initial migration creates tables from current model metadata. This revision
therefore inspects the table first so fresh databases and databases created from
the original schema both upgrade cleanly.
"""

import sqlalchemy as sa
from alembic import op

revision = "20260923_0002"
down_revision = "20260923_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("articles")}
    foreign_keys = inspector.get_foreign_keys("articles")
    has_job_fk = any(
        key.get("constrained_columns") == ["research_job_id"]
        and key.get("referred_table") == "processing_jobs"
        for key in foreign_keys
    )
    additions = {
        "collection_method": sa.Column("collection_method", sa.String(40), nullable=False, server_default="dataset_upload"),
        "content_kind": sa.Column("content_kind", sa.String(24), nullable=False, server_default="article_page"),
        "search_query": sa.Column("search_query", sa.Text(), nullable=True),
        "discovery_url": sa.Column("discovery_url", sa.String(2048), nullable=True),
        "research_job_id": sa.Column("research_job_id", sa.Integer(), nullable=True),
    }
    missing = [name for name in additions if name not in columns]
    if missing or not has_job_fk:
        with op.batch_alter_table("articles") as batch_op:
            for name in missing:
                batch_op.add_column(additions[name])
            if not has_job_fk:
                batch_op.create_foreign_key(
                    "fk_articles_research_job_id_processing_jobs",
                    "processing_jobs",
                    ["research_job_id"],
                    ["id"],
                    ondelete="SET NULL",
                )

    inspector = sa.inspect(bind)
    index_names = {index["name"] for index in inspector.get_indexes("articles")}
    if "ix_articles_research_job_id" not in index_names:
        op.create_index("ix_articles_research_job_id", "articles", ["research_job_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    index_names = {index["name"] for index in inspector.get_indexes("articles")}
    if "ix_articles_research_job_id" in index_names:
        op.drop_index("ix_articles_research_job_id", table_name="articles")
    columns = {column["name"] for column in inspector.get_columns("articles")}
    if "research_job_id" in columns:
        with op.batch_alter_table("articles") as batch_op:
            for key in inspector.get_foreign_keys("articles"):
                if key.get("constrained_columns") == ["research_job_id"]:
                    if key.get("name"):
                        batch_op.drop_constraint(key["name"], type_="foreignkey")
            for name in ("research_job_id", "discovery_url", "search_query", "content_kind", "collection_method"):
                if name in columns:
                    batch_op.drop_column(name)
