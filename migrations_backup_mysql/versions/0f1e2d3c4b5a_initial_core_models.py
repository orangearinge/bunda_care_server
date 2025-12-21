"""initial core models

Revision ID: 0f1e2d3c4b5a
Revises: 
Create Date: 2025-11-09 14:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0f1e2d3c4b5a'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    insp = sa.inspect(conn)

    if not insp.has_table('roles'):
        op.create_table(
            'roles',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('name', sa.String(length=50), nullable=False, unique=True),
            sa.Column('description', sa.String(length=255), nullable=True),
        )

    if not insp.has_table('users'):
        op.create_table(
            'users',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('name', sa.String(length=100), nullable=True),
            sa.Column('email', sa.String(length=120), nullable=True, unique=True),
            sa.Column('password', sa.String(length=255), nullable=True),
            sa.Column('role_id', sa.Integer(), sa.ForeignKey('roles.id'), nullable=True),
        )

    if not insp.has_table('user_preferences'):
        op.create_table(
            'user_preferences',
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), primary_key=True),
            sa.Column('role', sa.String(length=50), nullable=False),
            sa.Column('height_cm', sa.Integer(), nullable=True),
            sa.Column('weight_kg', sa.Numeric(6, 2), nullable=True),
            sa.Column('age_year', sa.Integer(), nullable=True),
            sa.Column('gestational_age_week', sa.Integer(), nullable=True),
            sa.Column('belly_circumference_cm', sa.Integer(), nullable=True),
            sa.Column('lila_cm', sa.Integer(), nullable=True),
            sa.Column('lactation_ml', sa.Integer(), nullable=True),
            sa.Column('food_prohibitions', sa.JSON(), nullable=True),
            sa.Column('allergens', sa.JSON(), nullable=True),
            sa.Column('calorie_target', sa.Integer(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        )

    if not insp.has_table('food_ingredients'):
        op.create_table(
            'food_ingredients',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('name', sa.String(length=150), nullable=False, unique=True),
            sa.Column('alt_names', sa.Text(), nullable=True),
            sa.Column('calories', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('protein_g', sa.Numeric(8, 2), nullable=False, server_default='0'),
            sa.Column('carbs_g', sa.Numeric(8, 2), nullable=False, server_default='0'),
            sa.Column('fat_g', sa.Numeric(8, 2), nullable=False, server_default='0'),
        )

    if not insp.has_table('food_menus'):
        op.create_table(
            'food_menus',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('name', sa.String(length=150), nullable=False),
            sa.Column('meal_type', sa.String(length=20), nullable=False),
            sa.Column('tags', sa.Text(), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        )

    if not insp.has_table('food_menu_ingredients'):
        op.create_table(
            'food_menu_ingredients',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('menu_id', sa.Integer(), sa.ForeignKey('food_menus.id'), nullable=False),
            sa.Column('ingredient_id', sa.Integer(), sa.ForeignKey('food_ingredients.id'), nullable=False),
            sa.Column('quantity_g', sa.Numeric(8, 2), nullable=False),
            sa.UniqueConstraint('menu_id', 'ingredient_id', name='uq_menu_ingredient'),
        )


def downgrade():
    # Drop in reverse dependency order
    for tbl in (
        'food_menu_ingredients',
        'food_menus',
        'food_ingredients',
        'user_preferences',
        'users',
        'roles',
    ):
        try:
            op.drop_table(tbl)
        except Exception:
            pass
