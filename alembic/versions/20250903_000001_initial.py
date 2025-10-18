"""initial schema with all features

Revision ID: 20250903_000001
Revises: 
Create Date: 2025-09-03 00:00:01
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '20250903_000001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Создание ENUM типов
    item_type = postgresql.ENUM('service', 'digital', 'offline', name='item_type')
    item_type.create(op.get_bind(), checkfirst=True)
    
    pricing_type = postgresql.ENUM('per_hour', 'per_service', name='pricing_type')
    pricing_type.create(op.get_bind(), checkfirst=True)
    
    payment_method = postgresql.ENUM('CARD_RF', 'SBP_QR', name='payment_method')
    payment_method.create(op.get_bind(), checkfirst=True)
    
    order_status = postgresql.ENUM('created', 'pending', 'paid', 'failed', 'canceled', name='order_status')
    order_status.create(op.get_bind(), checkfirst=True)
    
    # Таблица users
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('tg_id', sa.BigInteger(), nullable=False),
        sa.Column('username', sa.String(length=64), nullable=True),
        sa.Column('first_name', sa.String(length=64), nullable=True),
        sa.Column('last_name', sa.String(length=64), nullable=True),
        sa.Column('language_code', sa.String(length=64), nullable=True),
        sa.Column('is_bot', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_users_tg_id', 'users', ['tg_id'], unique=True)
    
    # Таблица items (с полями для offline/physical товаров)
    op.create_table(
        'items',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('price_minor', sa.Integer(), nullable=False),
        sa.Column('item_type', sa.Enum('service', 'digital', 'offline', name='item_type'), nullable=False),
        sa.Column('image_file_id', sa.String(length=256), nullable=True),
        
        # Service fields
        sa.Column('pricing_type', sa.Enum('per_hour', 'per_service', name='pricing_type'), nullable=True),
        sa.Column('service_admin_contact', sa.String(length=128), nullable=True),
        
        # Digital fields
        sa.Column('delivery_type', sa.String(length=20), nullable=True),  # file/github/codes
        sa.Column('digital_file_path', sa.String(length=512), nullable=True),
        sa.Column('github_repo_read_grant', sa.String(length=256), nullable=True),
        
        # Physical/Offline fields (соответствуют модели)
        sa.Column('stock', sa.Integer(), nullable=True),
        sa.Column('shipping_info_text', sa.Text(), nullable=True),
        
        sa.Column('is_visible', sa.Boolean(), nullable=False, server_default=sa.text('true')),
    )
    
    # Таблица orders
    op.create_table(
        'orders',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('item_id', sa.Integer(), sa.ForeignKey('items.id', ondelete='SET NULL'), nullable=True),
        sa.Column('amount_minor', sa.Integer(), nullable=False),
        sa.Column('currency', sa.String(length=8), nullable=False, server_default='RUB'),
        sa.Column('payment_method', sa.Enum('CARD_RF','SBP_QR', name='payment_method'), nullable=False),
        sa.Column('status', sa.Enum('created', 'pending', 'paid', 'failed', 'canceled', name='order_status'), nullable=False, server_default='created'),
        sa.Column('fk_order_id', sa.String(length=64), nullable=True),
        sa.Column('fk_payment_url', sa.String(length=1024), nullable=True),
        sa.Column('buyer_tg_id', sa.String(length=64), nullable=True),
    )
    
    # Таблица purchases (с полями доставки)
    op.create_table(
        'purchases',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('order_id', sa.Integer(), sa.ForeignKey('orders.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('item_id', sa.Integer(), sa.ForeignKey('items.id', ondelete='SET NULL'), nullable=True),
        sa.Column('delivery_info', sa.String(length=1024), nullable=True),
        
        # Offline delivery fields (соответствуют модели Purchase)
        sa.Column('delivery_fullname', sa.String(length=200), nullable=True),
        sa.Column('delivery_phone', sa.String(length=20), nullable=True),
        sa.Column('delivery_address', sa.Text(), nullable=True),
        sa.Column('delivery_comment', sa.Text(), nullable=True),
    )
    
    # Таблица item_codes
    op.create_table(
        'item_codes',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('item_id', sa.Integer(), sa.ForeignKey('items.id', ondelete='CASCADE'), nullable=False),
        sa.Column('code', sa.String(length=512), nullable=False),
        sa.Column('is_sold', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('sold_order_id', sa.Integer(), nullable=True),
    )
    
    # Таблица cart_items
    op.create_table(
        'cart_items',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('item_id', sa.Integer(), sa.ForeignKey('items.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_cart_items_user', 'cart_items', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_cart_items_user', table_name='cart_items')
    op.drop_table('cart_items')
    op.drop_table('item_codes')
    op.drop_table('purchases')
    op.drop_table('orders')
    op.drop_table('items')
    op.drop_index('ix_users_tg_id', table_name='users')
    op.drop_table('users')
    
    order_status = postgresql.ENUM('created', 'pending', 'paid', 'failed', 'canceled', name='order_status')
    order_status.drop(op.get_bind(), checkfirst=True)
    
    payment_method = postgresql.ENUM('CARD_RF', 'SBP_QR', name='payment_method')
    payment_method.drop(op.get_bind(), checkfirst=True)
    
    pricing_type = postgresql.ENUM('per_hour', 'per_service', name='pricing_type')
    pricing_type.drop(op.get_bind(), checkfirst=True)
    
    item_type = postgresql.ENUM('service', 'digital', 'offline', name='item_type')
    item_type.drop(op.get_bind(), checkfirst=True)