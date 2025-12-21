"""add food_label_map

Revision ID: 1907cb40d747
Revises: b1a2c3d4e5f6
Create Date: 2025-11-09 01:34:01.344036

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1907cb40d747'
down_revision = 'b1a2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'food_label_map',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('label', sa.String(length=150), nullable=False),
        sa.Column('normalized_label', sa.String(length=150), nullable=True),
        sa.Column('ingredient_id', sa.Integer(), sa.ForeignKey('food_ingredients.id', ondelete='CASCADE'), nullable=False),
    )
    op.create_index('ix_food_label_map_label', 'food_label_map', ['label'], unique=True)

    # Seed initial mappings from dataset classes -> FoodIngredient names
    conn = op.get_bind()

    mapping = [
        ("nasi-putih", "nasi", "nasi"),
        ("daging-ayam", "ayam", "ayam"),
        ("daging-sapi", "sapi", "sapi"),
        ("udang", "udang", "udang"),
        ("telur", "telur", "telur"),
        ("timun", "timun", "timun"),
        ("tomat", "tomat", "tomat"),
        ("wortel", "wortel", "wortel"),
        ("brokoli", "brokoli", "brokoli"),
        ("kol", "kol", "kol"),
        ("apel", "apel", "apel"),
        ("pisang", "pisang", "pisang"),
    ]

    for label, normalized, ing_name in mapping:
        try:
            ing_id = conn.execute(
                sa.text("SELECT id FROM food_ingredients WHERE lower(name)=:n"),
                {"n": ing_name.lower()},
            ).scalar()
            if not ing_id:
                continue
            exists = conn.execute(
                sa.text("SELECT 1 FROM food_label_map WHERE label=:l"),
                {"l": label},
            ).scalar()
            if not exists:
                conn.execute(
                    sa.text(
                        "INSERT INTO food_label_map (label, normalized_label, ingredient_id) VALUES (:l, :nl, :iid)"
                    ),
                    {"l": label, "nl": normalized, "iid": ing_id},
                )
        except Exception:
            # ignore insert errors to keep migration idempotent
            pass


def downgrade():
    op.drop_index('ix_food_label_map_label', table_name='food_label_map')
    op.drop_table('food_label_map')
