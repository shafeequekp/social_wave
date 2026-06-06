"""add chat history table

Revision ID: b8c4e91d2f03
Revises: 837f00bd98d0
Create Date: 2026-06-06 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b8c4e91d2f03'
down_revision: Union[str, Sequence[str], None] = '837f00bd98d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'ai chat histories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('question', sa.Text(), nullable=True),
        sa.Column('answer', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_ai chat histories_id'),
        'ai chat histories',
        ['id'],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_ai chat histories_id'), table_name='ai chat histories')
    op.drop_table('ai chat histories')
