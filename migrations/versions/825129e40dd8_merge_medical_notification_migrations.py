"""merge medical notification migrations

Revision ID: 825129e40dd8
Revises: create_medical_notifications, a61481083f3e
Create Date: 2026-08-22 20:25:17.744137

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "825129e40dd8"

down_revision: Union[
    str,
    Sequence[str],
    None
] = (
    "create_medical_notifications",
    "a61481083f3e",
)

branch_labels: Union[
    str,
    Sequence[str],
    None
] = None

depends_on: Union[
    str,
    Sequence[str],
    None
] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass