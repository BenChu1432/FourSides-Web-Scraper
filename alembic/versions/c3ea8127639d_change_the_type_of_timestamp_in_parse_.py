"""change the type of timestamp in parse_failures from Timestamp to Int

Revision ID: c3ea8127639d
Revises: fafc77d3c9cd
Create Date: 2025-07-13 22:40:26.832255

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c3ea8127639d'
down_revision: Union[str, Sequence[str], None] = 'fafc77d3c9cd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('scrape_failures', 'timestamp',
               existing_type=postgresql.TIMESTAMP(),
               type_=sa.Integer(),
               postgresql_using="EXTRACT(EPOCH FROM timestamp)::integer")
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('scrape_failures', 'timestamp',
               existing_type=sa.Integer(),
               type_=postgresql.TIMESTAMP(),
               postgresql_using="to_timestamp(timestamp)")
    # ### end Alembic commands ###
