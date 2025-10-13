"""add cart_items table

Revision ID: 20250113_add_cart
Revises: 20250903_000001
Create Date: 2025-01-13 12:00:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '20250113_add_cart'
down_revision = '20250903_000001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'cart_items',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('item_id', sa.Integer(), sa.ForeignKey('items.id', ondelete='CASCADE'), nullable=False),
        sa.Column('added_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_cart_user_id', 'cart_items', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_cart_user_id', table_name='cart_items')
    op.drop_table('cart_items')