"""add enums

Revision ID: b106086f7856
Revises: c9955877226e
Create Date: 2025-07-13 16:15:04.181335

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from alembic_postgresql_enum import TableReference

# revision identifiers, used by Alembic.
revision: str = 'b106086f7856'
down_revision: Union[str, Sequence[str], None] = 'c9955877226e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.sync_enum_values(
        enum_schema='public',
        enum_name='errortypeenum',
        new_values=['UNMAPPED_MEDIA', 'PARSING_FAILURE', 'PARSING_ERROR', 'ZERO_URLS_FETCHED'],
        affected_columns=[TableReference(table_schema='public', table_name='scrape_failures', column_name='failure_type')],
        enum_values_to_rename=[],
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.sync_enum_values(
        enum_schema='public',
        enum_name='errortypeenum',
        new_values=['UNMAPPED_MEDIA', 'NO_URLS_FETCHED', 'PARSING_FAILED', 'FETCH_FAILED'],
        affected_columns=[TableReference(table_schema='public', table_name='scrape_failures', column_name='failure_type')],
        enum_values_to_rename=[],
    )
    # ### end Alembic commands ###
