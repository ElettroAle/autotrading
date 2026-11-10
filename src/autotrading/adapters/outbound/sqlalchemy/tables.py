from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    LargeBinary,
    MetaData,
    Numeric,
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
    UniqueConstraint("id", "tenant_id", name="accounts_id_tenant_unique"),
)

# Owned by a tenant like the accounts; the client order id given by the platform is the key (ADR 0022).
orders = Table(
    "orders",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("tenant_id", Uuid, ForeignKey("tenants.id"), nullable=False),
    Column("account_id", Uuid, nullable=False),
    Column("origin", Text, nullable=False),
    Column("user_id", Text),
    Column("coin", Text, nullable=False),
    Column("direction", Text, nullable=False),
    Column("reduce_only", Boolean, nullable=False),
    Column("leverage", Integer, nullable=False),
    Column("requested_size", Numeric, nullable=False),
    Column("slippage", Numeric, nullable=False),
    Column("status", Text, nullable=False),
    Column("filled_size", Numeric),
    Column("average_price", Numeric),
    Column("fee", Numeric),
    Column("realized_pnl", Numeric),
    Column("executed_at", DateTime(timezone=True)),
    Column("rejection_reason", Text),
    Column("exchange_message", Text),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    ForeignKeyConstraint(
        ["account_id", "tenant_id"], ["accounts.id", "accounts.tenant_id"], name="orders_account_of_tenant"
    ),
)

verification_runs = Table(
    "verification_runs",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("tenant_id", Uuid, ForeignKey("tenants.id"), nullable=False),
    Column("account_id", Uuid, nullable=False),
    Column("user_id", Text, nullable=False),
    Column("environment", Text, nullable=False),
    Column("started_at", DateTime(timezone=True), nullable=False),
    Column("outcome", Text, nullable=False),
    Column("total_fee", Numeric, nullable=False),
    Column("realized_pnl", Numeric, nullable=False),
    Column("warning", Text),
    Column("steps", JSON, nullable=False),
    ForeignKeyConstraint(
        ["account_id", "tenant_id"], ["accounts.id", "accounts.tenant_id"], name="verification_runs_account_of_tenant"
    ),
)
