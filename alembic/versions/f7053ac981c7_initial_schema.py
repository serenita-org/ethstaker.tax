"""Initial schema

Revision ID: f7053ac981c7
Revises: 
Create Date: 2021-02-23 22:35:07.803771

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f7053ac981c7'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('balance',
        sa.Column('slot', sa.Integer(), nullable=False),
        sa.Column('validator_index', sa.Integer(), nullable=False),
        sa.Column('balance', sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint('slot', 'validator_index')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('balance')
    # ### end Alembic commands ###
