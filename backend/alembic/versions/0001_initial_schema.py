"""initial CargoLens schema

Revision ID: 0001
"""

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    for name, cols in {
        "users": [
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("email", sa.String(), unique=True, nullable=False),
            sa.Column("password_hash", sa.String(), nullable=False),
            sa.Column("role", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime()),
            sa.Column("updated_at", sa.DateTime()),
        ],
        "shipments": [
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("reference", sa.String(), unique=True, nullable=False),
            sa.Column("supplier_name", sa.String(), nullable=False),
            sa.Column("supplier_country", sa.String()),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("approval_status", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime()),
            sa.Column("updated_at", sa.DateTime()),
        ],
    }.items():
        op.create_table(name, *cols)


def downgrade():
    op.drop_table("shipments")
    op.drop_table("users")
