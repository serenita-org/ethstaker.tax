"""validator metadata

Revision ID: 0a98fcf0416d
Revises: 072ff1540642
Create Date: 2024-01-21 16:20:41.706703

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0a98fcf0416d'
down_revision = '072ff1540642'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('validator',
    sa.Column('validator_index', sa.Integer(), nullable=False),
    sa.Column('pubkey', sa.String(length=98), nullable=False),
    sa.PrimaryKeyConstraint('validator_index')
    )
    op.create_index(op.f('ix_validator_pubkey'), 'validator', ['pubkey'], unique=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_validator_pubkey'), table_name='validator')
    op.drop_table('validator')
    # ### end Alembic commands ###
