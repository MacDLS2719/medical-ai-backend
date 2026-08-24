from alembic import op
import sqlalchemy as sa


revision = "c91f4a72d8e1"
down_revision = "0587e6432416"
branch_labels = None
depends_on = None


def upgrade() -> None:

    op.add_column(
        "users",
        sa.Column(
            "language",
            sa.String(length=10),
            nullable=False,
            server_default="es"
        )
    )


def downgrade() -> None:

    op.drop_column(
        "users",
        "language"
    )