"""drop food_logs

Revision ID: 10a60ac40e5c
Revises: 853ba7a43d84
Create Date: 2025-11-08 19:34:45.747123
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '10a60ac40e5c'
down_revision = '853ba7a43d84'
branch_labels = None
depends_on = None


def upgrade():
    # Drop table food_logs if it exists
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if insp.has_table('food_logs'):
        op.drop_table("food_logs")


def downgrade():
    # Recreate table (sesuaikan kolom dengan versi terakhir tabel sebelum dihapus)
    op.create_table(
        "food_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("food_name", sa.String(255), nullable=False),
        sa.Column("calories", sa.Float(), nullable=True),
        sa.Column("logged_at", sa.DateTime(), nullable=False),
    )
