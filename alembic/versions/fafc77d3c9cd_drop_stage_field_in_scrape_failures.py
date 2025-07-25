"""Drop stage field in scrape_failures

Revision ID: fafc77d3c9cd
Revises: b33eb2f60e79
Create Date: 2025-07-13 22:16:17.446410

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fafc77d3c9cd'
down_revision: Union[str, Sequence[str], None] = 'b33eb2f60e79'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('scrape_failures', 'stage')
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('scrape_failures', sa.Column('stage', sa.VARCHAR(), autoincrement=False, nullable=True))
    # ### end Alembic commands ###
