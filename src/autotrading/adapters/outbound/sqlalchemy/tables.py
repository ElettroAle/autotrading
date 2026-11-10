from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    MetaData,
    Table,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)

metadata = MetaData()

# Tenancy tables carry no row level security: ResolveTenantUseCase reads them before the tenant is known.
tenants = Table(
    "tenants",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

memberships = Table(
    "memberships",
    metadata,
    Column("user_id", Text, primary_key=True),
    Column("tenant_id", Uuid, ForeignKey("tenants.id"), nullable=False, unique=True),
)

# Owned by a tenant: row level security shows a transaction only the rows of the tenant it declares (ADR 0018).
accounts = Table(
    "accounts",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("tenant_id", Uuid, ForeignKey("tenants.id"), nullable=False),
    Column("name", Text, nullable=False),
    Column("exchange", Text, nullable=False),
    Column("exchange_account_fingerprint", Text, nullable=False),
    Column("credentials_key_version", Integer, nullable=False),
    Column("credentials_ciphertext", LargeBinary, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint("tenant_id", "name", name="accounts_name_unique_in_tenant"),
)
