"""initial

Revision ID: b1baea156217
Revises: 
Create Date: 2026-10-11 12:45:17.047509

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'b1baea156217'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('outbox',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('topic', sa.String(), nullable=False),
    sa.Column('payload', sa.JSON(), nullable=False),
    sa.Column('status', sa.Enum('pending', 'published', name='outbox_status'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('payment',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('amount', sa.Numeric(precision=18, scale=2), nullable=False),
    sa.Column('currency', sa.Enum('RUB', 'USD', 'EUR', name='currency'), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('meta_data', sa.JSON(), nullable=False),
    sa.Column('status', sa.Enum('pending', 'succeeded', 'failed', name='payment_status'), nullable=False),
    sa.Column('idempotency_key', sa.String(), nullable=False),
    sa.Column('webhook_url', sa.String(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('payment')
    op.drop_table('outbox')
