"""add table Stock

Revision ID: 8d4a7ee5996e
Revises:
Create Date: 2025-03-06 16:32:41.371275

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8d4a7ee5996e"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "stock",
        "price",
        existing_type=sa.Numeric(precision=13, scale=4),  # 기존 타입
        type_=sa.Float,  # 변경할 타입
        existing_nullable=False,
    )


def downgrade() -> None:
    """롤백 시: FLOAT -> DECIMAL 복구"""
    op.alter_column(
        "stock",
        "price",
        existing_type=sa.Float,
        type_=sa.Numeric(precision=13, scale=4),
        existing_nullable=False,
    )
