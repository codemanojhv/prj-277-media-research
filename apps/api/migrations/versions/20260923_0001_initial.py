"""Initial PRJ_277 schema."""

from alembic import op

from app.db.models import Base

revision = "20260923_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
