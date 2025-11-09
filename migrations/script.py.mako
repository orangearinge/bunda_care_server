"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade():
    op.add_column('food_logs', sa.Column('source_menu_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_food_logs_source_menu',
        'food_logs',
        'food_menus',
        ['source_menu_id'],
        ['id'],
        ondelete='SET NULL'
    )



def downgrade():
    op.drop_constraint('fk_food_logs_source_menu', 'food_logs', type_='foreignkey')
    op.drop_column('food_logs', 'source_menu_id')
