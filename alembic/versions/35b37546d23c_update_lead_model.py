"""update lead model

Revision ID: 35b37546d23c
Revises: 394b528f10e2
Create Date: 2026-09-03 15:21:28.139193

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '35b37546d23c'
down_revision: Union[str, Sequence[str], None] = '394b528f10e2'
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
