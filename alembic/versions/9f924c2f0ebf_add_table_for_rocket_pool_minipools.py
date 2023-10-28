"""Add table for Rocket Pool minipools

Revision ID: 9f924c2f0ebf
Revises: 06aab3e116c5
Create Date: 2023-10-28 13:41:04.349325

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9f924c2f0ebf'
down_revision = '06aab3e116c5'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('rocket_pool_minipool',
    sa.Column('minipool_index', sa.Integer(), nullable=False),
    sa.Column('validator_index', sa.Integer(), nullable=False),
    sa.Column('node_address', sa.String(length=42), nullable=False),
    sa.Column('node_deposit_balance', sa.String(length=20), nullable=False),
    sa.Column('fee', sa.Numeric(precision=19), nullable=False),
    sa.Column('bond_reduced_timestamp', sa.TIMESTAMP(timezone=True), nullable=True),
    sa.Column('bond_pre_reduction_value_wei', sa.Numeric(precision=27), nullable=True),
    sa.PrimaryKeyConstraint('minipool_index')
    )
    op.create_index(op.f('ix_rocket_pool_minipool_validator_index'), 'rocket_pool_minipool', ['validator_index'], unique=False)
    op.create_table('rocket_pool_reward_period',
    sa.Column('reward_period_index', sa.Integer(), nullable=False),
    sa.Column('reward_period_end_time', sa.TIMESTAMP(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('reward_period_index')
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
    op.drop_table('rocket_pool_reward_period')
    op.drop_index(op.f('ix_rocket_pool_minipool_validator_index'), table_name='rocket_pool_minipool')
    op.drop_table('rocket_pool_minipool')
    # ### end Alembic commands ###