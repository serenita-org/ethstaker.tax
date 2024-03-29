"""Remove v1 Rocket Pool tables

Revision ID: e9d91d6ad279
Revises: 6eb67fa3774f
Create Date: 2024-01-21 11:09:12.074361

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'e9d91d6ad279'
down_revision = '6eb67fa3774f'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('rocket_pool_bond_reduction')
    op.drop_index('ix_rocket_pool_minipool_minipool_address', table_name='rocket_pool_minipool')
    op.drop_index('ix_rocket_pool_minipool_validator_index', table_name='rocket_pool_minipool')
    op.drop_table('rocket_pool_minipool')
    op.drop_table('rocket_pool_reward')
    op.drop_table('rocket_pool_reward_period')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('rocket_pool_reward',
    sa.Column('node_address', sa.VARCHAR(length=42), autoincrement=False, nullable=False),
    sa.Column('reward_collateral_rpl', sa.NUMERIC(precision=27, scale=0), autoincrement=False, nullable=False),
    sa.Column('reward_smoothing_pool_wei', sa.NUMERIC(precision=27, scale=0), autoincrement=False, nullable=False),
    sa.Column('reward_period_index', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['reward_period_index'], ['rocket_pool_reward_period.reward_period_index'], name='rocket_pool_reward_reward_period_index_fkey'),
    sa.PrimaryKeyConstraint('node_address', 'reward_period_index', name='rocket_pool_reward_pkey')
    )
    op.create_table('rocket_pool_bond_reduction',
    sa.Column('timestamp', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=False),
    sa.Column('prev_node_fee', sa.NUMERIC(precision=19, scale=0), autoincrement=False, nullable=False),
    sa.Column('prev_bond_value', sa.NUMERIC(precision=27, scale=0), autoincrement=False, nullable=True),
    sa.Column('minipool_address', sa.VARCHAR(length=42), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['minipool_address'], ['rocket_pool_minipool.minipool_address'], name='rocket_pool_bond_reduction_minipool_address_fkey'),
    sa.PrimaryKeyConstraint('timestamp', 'minipool_address', name='rocket_pool_bond_reduction_pkey')
    )
    op.create_table('rocket_pool_reward_period',
    sa.Column('reward_period_index', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('reward_period_end_time', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=False),
    sa.PrimaryKeyConstraint('reward_period_index', name='rocket_pool_reward_period_pkey')
    )
    op.create_table('rocket_pool_minipool',
    sa.Column('minipool_index', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('minipool_address', sa.VARCHAR(length=42), autoincrement=False, nullable=False),
    sa.Column('validator_index', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('node_address', sa.VARCHAR(length=42), autoincrement=False, nullable=False),
    sa.Column('node_deposit_balance', sa.VARCHAR(length=20), autoincrement=False, nullable=False),
    sa.Column('fee', sa.NUMERIC(precision=19, scale=0), autoincrement=False, nullable=False),
    sa.PrimaryKeyConstraint('minipool_index', name='rocket_pool_minipool_pkey')
    )
    op.create_index('ix_rocket_pool_minipool_validator_index', 'rocket_pool_minipool', ['validator_index'], unique=False)
    op.create_index('ix_rocket_pool_minipool_minipool_address', 'rocket_pool_minipool', ['minipool_address'], unique=False)
    # ### end Alembic commands ###
