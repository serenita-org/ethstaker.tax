"""Add reward_processed_ok to BlockReward

Revision ID: 06aab3e116c5
Revises: 09714230640a
Create Date: 2023-10-24 21:10:28.304261

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '06aab3e116c5'
down_revision = '09714230640a'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('block_reward', sa.Column('reward_processed_ok', sa.Boolean(), nullable=False))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('block_reward', 'reward_processed_ok')
    # ### end Alembic commands ###