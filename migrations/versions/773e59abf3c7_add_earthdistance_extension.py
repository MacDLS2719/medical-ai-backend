"""Add earthdistance extension

Revision ID: 773e59abf3c7
Revises: db0152e3550e
Create Date: 2026-09-29 22:58:01.605828

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '773e59abf3c7'
down_revision: Union[str, Sequence[str], None] = 'db0152e3550e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
