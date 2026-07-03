"""add spraying care type

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-03

"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "INSERT INTO care_types (code, name) VALUES ('spraying', 'Опрыскивание') "
        "ON CONFLICT (code) DO NOTHING"
    )


def downgrade() -> None:
    op.execute("DELETE FROM care_types WHERE code = 'spraying'")
