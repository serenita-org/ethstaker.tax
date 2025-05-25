"""Allow for multiple withdrawals in single slot

Revision ID: 77620d0cd8c8
Revises: d0f0663435bf
Create Date: 2025-05-25 11:31:57.345348

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '77620d0cd8c8'
down_revision = 'd0f0663435bf'
branch_labels = None
depends_on = None


def upgrade():
    # Step 1: Drop existing primary key constraint
    # (composite primary key of slot+validator idx no longer works post-Pectra
    #  since multiple withdrawals for the same validator can be processed in the
    #  same slot... e.g. https://beaconcha.in/slot/11749280#withdrawals )
    op.drop_constraint('withdrawal_pkey', 'withdrawal', type_='primary')

    # Step 2: Add new auto-incrementing 'id' column
    op.add_column('withdrawal', sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True))

    # Step 3: Set 'id' as the new primary key
    op.create_primary_key('withdrawal_pkey', 'withdrawal', ['id'])


def downgrade():
    op.drop_constraint('withdrawal_pkey', 'withdrawal', type_='primary')
    op.drop_column('withdrawal', 'id')
    op.create_primary_key('withdrawal_pkey', 'withdrawal', ['slot', 'validator_index'])
