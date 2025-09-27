from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0002_product_meta"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create product_templates table
    op.create_table(
        "product_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=160), nullable=False, unique=True),
        sa.Column("schema", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )

    # Add description, attributes, template_id to products
    op.add_column("products", sa.Column("description", sa.String(length=5000), nullable=True))
    op.add_column("products", sa.Column("attributes", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("products", sa.Column("template_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_products_template", "products", "product_templates", ["template_id"], ["id"], ondelete=None
    )


def downgrade() -> None:
    op.drop_constraint("fk_products_template", "products", type_="foreignkey")
    op.drop_column("products", "template_id")
    op.drop_column("products", "attributes")
    op.drop_column("products", "description")
    op.drop_table("product_templates")
