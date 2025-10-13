"""add offline item type

Revision ID: add_offline_type
Revises: add_cart
Create Date: 2025-01-13 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_offline_type'
down_revision = 'add_cart'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Добавляем новый тип OFFLINE в enum
    op.execute("ALTER TYPE item_type ADD VALUE IF NOT EXISTS 'offline'")
    
    # Добавляем поля для данных доставки в таблицу purchases
    op.add_column('purchases', sa.Column('delivery_phone', sa.String(20), nullable=True))
    op.add_column('purchases', sa.Column('delivery_address', sa.Text(), nullable=True))
    op.add_column('purchases', sa.Column('delivery_fullname', sa.String(200), nullable=True))
    op.add_column('purchases', sa.Column('delivery_comment', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('purchases', 'delivery_comment')
    op.drop_column('purchases', 'delivery_fullname')
    op.drop_column('purchases', 'delivery_address')
    op.drop_column('purchases', 'delivery_phone')
    # Примечание: удаление значения из enum требует более сложной процедуры