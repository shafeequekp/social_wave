"""created field changes

Revision ID: fb5830bb20ee
Revises: b8c4e91d2f03
Create Date: 2026-06-06 17:57:22.780812

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'fb5830bb20ee'
down_revision: Union[str, Sequence[str], None] = 'b8c4e91d2f03'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        'UPDATE "ai chat histories" SET created_at = NOW() WHERE created_at IS NULL'
    )
    op.alter_column(
        'ai chat histories',
        'created_at',
        existing_type=postgresql.TIMESTAMP(),
        type_=sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text('now()'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        'ai chat histories',
        'created_at',
        existing_type=sa.DateTime(timezone=True),
        type_=postgresql.TIMESTAMP(),
        nullable=True,
        server_default=None,
    )
