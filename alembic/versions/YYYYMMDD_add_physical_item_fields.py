"""Add stock and shipping_info_text for physical items

Revision ID: <generate_new>
Revises: <previous_revision>
Create Date: 2025-01-XX XX:XX:XX.XXXXXX

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '<generate_new>'
down_revision = '<previous_revision>'  # ID миграции 20250113_add_offline_item_type
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Добавляем поле для учета остатков физических товаров
    op.add_column('items', sa.Column('stock', sa.Integer(), nullable=True))
    
    # Добавляем поле для кастомного текста запроса адреса доставки
    op.add_column('items', sa.Column('shipping_info_text', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('items', 'shipping_info_text')
    op.drop_column('items', 'stock')