"""fractional care intervals

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-03

"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Дробные интервалы: «2-3 раза в неделю» = раз в 2.33 дня
    op.alter_column(
        "plant_care_schedules",
        "interval_days",
        existing_type=sa.Integer(),
        type_=sa.Float(),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "plant_care_schedules",
        "interval_days",
        existing_type=sa.Float(),
        type_=sa.Integer(),
        existing_nullable=False,
        postgresql_using="round(interval_days)::integer",
    )
