"""Add stock and shipping_info_text for physical items

Revision ID: <generate_new>
Revises: <previous_revision>
Create Date: 2025-01-XX XX:XX:XX.XXXXXX

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '<generate_new>'
down_revision = '<previous_revision>'  # ID �������� 20250113_add_offline_item_type
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ��������� ���� ��� ����� �������� ���������� �������
    op.add_column('items', sa.Column('stock', sa.Integer(), nullable=True))
    
    # ��������� ���� ��� ���������� ������ ������� ������ ��������
    op.add_column('items', sa.Column('shipping_info_text', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('items', 'shipping_info_text')
    op.drop_column('items', 'stock')