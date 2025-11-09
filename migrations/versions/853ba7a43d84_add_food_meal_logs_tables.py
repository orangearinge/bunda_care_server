"""add food_meal_logs tables

Revision ID: 853ba7a43d84
Revises: 8e278c460cbd
Create Date: 2025-11-08 18:11:32.784743

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '853ba7a43d84'
down_revision = '8e278c460cbd'
branch_labels = None
depends_on = None


def upgrade():
    # Create food_meal_logs table
    op.create_table(
        'food_meal_logs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('menu_id', sa.Integer(), sa.ForeignKey('food_menus.id'), nullable=False),
        sa.Column('total_calories', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_protein_g', sa.Numeric(10, 2), nullable=False, server_default='0'),
        sa.Column('total_carbs_g', sa.Numeric(10, 2), nullable=False, server_default='0'),
        sa.Column('total_fat_g', sa.Numeric(10, 2), nullable=False, server_default='0'),
        sa.Column('servings', sa.Numeric(8, 2), nullable=False, server_default='1'),
        sa.Column('logged_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )

    # Create food_meal_log_items table
    op.create_table(
        'food_meal_log_items',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('meal_log_id', sa.Integer(), sa.ForeignKey('food_meal_logs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('ingredient_id', sa.Integer(), sa.ForeignKey('food_ingredients.id'), nullable=False),
        sa.Column('quantity_g', sa.Numeric(8, 2), nullable=False),
        sa.Column('calories', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('protein_g', sa.Numeric(10, 2), nullable=False, server_default='0'),
        sa.Column('carbs_g', sa.Numeric(10, 2), nullable=False, server_default='0'),
        sa.Column('fat_g', sa.Numeric(10, 2), nullable=False, server_default='0'),
    )

    # Helpful indexes
    op.create_index('ix_food_meal_logs_user_logged', 'food_meal_logs', ['user_id', 'logged_at'])
    op.create_index('ix_food_meal_log_items_meal', 'food_meal_log_items', ['meal_log_id'])

    # Ensure FK on existing food_logs.source_menu_id -> food_menus.id
    op.create_foreign_key(
        'fk_food_logs_source_menu',
        'food_logs',
        'food_menus',
        ['source_menu_id'],
        ['id'],
        ondelete='SET NULL'
    )


def downgrade():
    # Drop FK on food_logs, ignore if not exists
    try:
        op.drop_constraint('fk_food_logs_source_menu', 'food_logs', type_='foreignkey')
    except Exception:
        pass

    # Drop indexes safely
    try:
        op.drop_index('ix_food_meal_log_items_meal', table_name='food_meal_log_items')
    except Exception:
        pass

    try:
        op.drop_index('ix_food_meal_logs_user_logged', table_name='food_meal_logs')
    except Exception:
        pass

    # Drop tables safely
    try:
        op.drop_table('food_meal_log_items')
    except Exception:
        pass

    try:
        op.drop_table('food_meal_logs')
    except Exception:
        pass

