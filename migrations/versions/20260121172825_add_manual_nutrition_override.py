"""add manual nutrition override

Revision ID: 20260121172825
Revises: d7396841509c
Create Date: 2026-01-21 17:28:25

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260121172825'
down_revision = 'd7396841509c'
branch_labels = None
depends_on = None


def upgrade():
    # Add manual nutrition override columns to food_menus
    op.add_column('food_menus', sa.Column('nutrition_is_manual', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('food_menus', sa.Column('serving_unit', sa.String(50), nullable=True))
    op.add_column('food_menus', sa.Column('manual_calories', sa.Integer(), nullable=True))
    op.add_column('food_menus', sa.Column('manual_protein_g', sa.Numeric(8, 2), nullable=True))
    op.add_column('food_menus', sa.Column('manual_carbs_g', sa.Numeric(8, 2), nullable=True))
    op.add_column('food_menus', sa.Column('manual_fat_g', sa.Numeric(8, 2), nullable=True))
    
    # Add display_quantity column to food_menu_ingredients for flexible text input
    op.add_column('food_menu_ingredients', sa.Column('display_quantity', sa.String(100), nullable=True))
    
    # Make quantity_g nullable to allow display-only ingredients
    op.alter_column('food_menu_ingredients', 'quantity_g',
                    existing_type=sa.Numeric(8, 2),
                    nullable=True)


def downgrade():
    # Remove columns from food_menus
    op.drop_column('food_menus', 'manual_fat_g')
    op.drop_column('food_menus', 'manual_carbs_g')
    op.drop_column('food_menus', 'manual_protein_g')
    op.drop_column('food_menus', 'manual_calories')
    op.drop_column('food_menus', 'serving_unit')
    op.drop_column('food_menus', 'nutrition_is_manual')
    
    # Remove display_quantity from food_menu_ingredients
    op.drop_column('food_menu_ingredients', 'display_quantity')
    
    # Restore quantity_g to NOT NULL
    op.alter_column('food_menu_ingredients', 'quantity_g',
                    existing_type=sa.Numeric(8, 2),
                    nullable=False)
