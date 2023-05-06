"""Store withdrawal address

Revision ID: 991c5c3c836a
Revises: 8a50cc3b105a
Create Date: 2023-05-05 10:21:39.539658

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '991c5c3c836a'
down_revision = '8a50cc3b105a'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('withdrawal_address',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('address', sa.String(length=42), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.add_column('withdrawal', sa.Column('withdrawal_address_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'withdrawal', 'withdrawal_address', ['withdrawal_address_id'], ['id'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'withdrawal', type_='foreignkey')
    op.drop_column('withdrawal', 'withdrawal_address_id')
    op.drop_table('withdrawal_address')
    # ### end Alembic commands ###
