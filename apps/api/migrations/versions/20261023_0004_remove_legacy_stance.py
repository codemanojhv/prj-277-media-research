"""Remove retired stance columns from local article analysis."""

import sqlalchemy as sa
from alembic import op

revision = "20261023_0004"
down_revision = "20261022_0003"
branch_labels = None
depends_on = None

RETIRED_COLUMNS = ("stance", "stance_target", "stance_confidence")


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "article_analysis" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("article_analysis")}
    retired = [name for name in RETIRED_COLUMNS if name in columns]
    if not retired:
        return

    for index in inspector.get_indexes("article_analysis"):
        if set(index.get("column_names") or ()) & set(retired) and index.get("name"):
            op.drop_index(index["name"], table_name="article_analysis")

    with op.batch_alter_table("article_analysis") as batch:
        for name in retired:
            batch.drop_column(name)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "article_analysis" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("article_analysis")}
    missing = [name for name in RETIRED_COLUMNS if name not in columns]
    if missing:
        additions = {
            "stance": sa.Column("stance", sa.String(20), nullable=False, server_default="unclear"),
            "stance_target": sa.Column("stance_target", sa.String(160), nullable=False, server_default="Unspecified target"),
            "stance_confidence": sa.Column("stance_confidence", sa.Float(), nullable=False, server_default="0"),
        }
        with op.batch_alter_table("article_analysis") as batch:
            for name in missing:
                batch.add_column(additions[name])

    indexes = {index["name"] for index in sa.inspect(bind).get_indexes("article_analysis")}
    if "ix_article_analysis_stance" not in indexes:
        op.create_index("ix_article_analysis_stance", "article_analysis", ["stance"])
