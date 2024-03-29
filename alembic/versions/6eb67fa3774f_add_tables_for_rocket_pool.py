"""Add tables for Rocket Pool

Revision ID: 6eb67fa3774f
Revises: 06aab3e116c5
Create Date: 2023-11-07 11:41:19.892440

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6eb67fa3774f'
down_revision = '06aab3e116c5'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('rocket_pool_minipool',
    sa.Column('minipool_index', sa.Integer(), nullable=False),
    sa.Column('minipool_address', sa.String(length=42), nullable=False),
    sa.Column('validator_index', sa.Integer(), nullable=False),
    sa.Column('node_address', sa.String(length=42), nullable=False),
    sa.Column('node_deposit_balance', sa.String(length=20), nullable=False),
    sa.Column('fee', sa.Numeric(precision=19), nullable=False),
    sa.PrimaryKeyConstraint('minipool_index')
    )
    op.create_index(op.f('ix_rocket_pool_minipool_minipool_address'), 'rocket_pool_minipool', ['minipool_address'], unique=True)
    op.create_index(op.f('ix_rocket_pool_minipool_validator_index'), 'rocket_pool_minipool', ['validator_index'], unique=False)
    op.create_table('rocket_pool_reward_period',
    sa.Column('reward_period_index', sa.Integer(), nullable=False),
    sa.Column('reward_period_end_time', sa.TIMESTAMP(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('reward_period_index')
    )
    op.create_table('rocket_pool_bond_reduction',
    sa.Column('timestamp', sa.TIMESTAMP(timezone=True), nullable=True),
    sa.Column('prev_node_fee', sa.Numeric(precision=19), nullable=False),
    sa.Column('prev_bond_value', sa.Numeric(precision=27), nullable=True),
    sa.Column('minipool_address', sa.String(length=42), nullable=False),
    sa.ForeignKeyConstraint(['minipool_address'], ['rocket_pool_minipool.minipool_address'], ),
    sa.PrimaryKeyConstraint('timestamp', 'minipool_address')
    )
    op.create_table('rocket_pool_reward',
    sa.Column('node_address', sa.String(length=42), nullable=False),
    sa.Column('reward_collateral_rpl', sa.Numeric(precision=27), nullable=False),
    sa.Column('reward_smoothing_pool_wei', sa.Numeric(precision=27), nullable=False),
    sa.Column('reward_period_index', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['reward_period_index'], ['rocket_pool_reward_period.reward_period_index'], ),
    sa.PrimaryKeyConstraint('node_address', 'reward_period_index')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('rocket_pool_reward')
    op.drop_table('rocket_pool_bond_reduction')
    op.drop_table('rocket_pool_reward_period')
    op.drop_index(op.f('ix_rocket_pool_minipool_validator_index'), table_name='rocket_pool_minipool')
    op.drop_index(op.f('ix_rocket_pool_minipool_minipool_address'), table_name='rocket_pool_minipool')
    op.drop_table('rocket_pool_minipool')
    # ### end Alembic commands ###
