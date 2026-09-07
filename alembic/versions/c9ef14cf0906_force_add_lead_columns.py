"""force add lead columns

Revision ID: c9ef14cf0906
Revises: 35b37546d23c
Create Date: 2026-09-03 15:44:09.475555

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c9ef14cf0906'
down_revision: Union[str, Sequence[str], None] = '35b37546d23c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TABLE leads ADD COLUMN IF NOT EXISTS timeline VARCHAR(100);")
    op.execute("ALTER TABLE leads ADD COLUMN IF NOT EXISTS preferred_contact_time VARCHAR(100);")
    op.execute("ALTER TABLE leads ADD COLUMN IF NOT EXISTS estimated_amount VARCHAR(100);")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('leads', 'estimated_amount')
    op.drop_column('leads', 'preferred_contact_time')
    op.drop_column('leads', 'timeline')
