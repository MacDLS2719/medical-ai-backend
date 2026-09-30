"""create doctor payment settings

Revision ID: 99cde91189d3
Revises: c2a49e17d0b6
Create Date: 2026-09-30 10:05:38.298406

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '99cde91189d3'
down_revision: Union[str, Sequence[str], None] = 'c2a49e17d0b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
