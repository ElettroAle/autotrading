from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Identity,
    Index,
    Integer,
    LargeBinary,
    MetaData,
    Numeric,
    Table,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
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
    # Empty once the account is removed: the row stays for its history, the credentials do not (ADR 0025).
    Column("credentials_key_version", Integer),
    Column("credentials_ciphertext", LargeBinary),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("removed_at", DateTime(timezone=True)),
    Index(
        "accounts_name_unique_in_tenant",
        "tenant_id",
        "name",
        unique=True,
        postgresql_where=text("removed_at IS NULL"),
    ),
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
    Column("flow_id", Uuid),
    Column("cycle_planned_at", DateTime(timezone=True)),
    Column("decision_asset", Text),
    ForeignKeyConstraint(
        ["account_id", "tenant_id"], ["accounts.id", "accounts.tenant_id"], name="orders_account_of_tenant"
    ),
    ForeignKeyConstraint(["flow_id", "tenant_id"], ["flows.id", "flows.tenant_id"], name="orders_flow_of_tenant"),
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

# At most one key per provider and tenant; replaced in place, deleted on removal (ADR 0029).
provider_keys = Table(
    "provider_keys",
    metadata,
    Column("tenant_id", Uuid, ForeignKey("tenants.id"), primary_key=True),
    Column("provider", Text, primary_key=True),
    Column("key_version", Integer, nullable=False),
    Column("ciphertext", LargeBinary, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

# A flow keeps its name unique among the flows of the tenant not archived (R1.1.1, ADR 0031).
flows = Table(
    "flows",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("tenant_id", Uuid, ForeignKey("tenants.id"), nullable=False),
    Column("account_id", Uuid, nullable=False),
    Column("name", Text, nullable=False),
    Column("status", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    ForeignKeyConstraint(
        ["account_id", "tenant_id"], ["accounts.id", "accounts.tenant_id"], name="flows_account_of_tenant"
    ),
    UniqueConstraint("id", "tenant_id", name="flows_id_tenant_unique"),
    Index(
        "flows_name_unique_in_tenant",
        "tenant_id",
        "name",
        unique=True,
        postgresql_where=text("status <> 'archived'"),
    ),
)

# Configuration versions are only ever added: a cycle can always be rebuilt with the one it used (R1.1.3).
flow_versions = Table(
    "flow_versions",
    metadata,
    Column("flow_id", Uuid, primary_key=True),
    Column("version", Integer, primary_key=True),
    Column("tenant_id", Uuid, nullable=False),
    Column("configuration", JSON, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    ForeignKeyConstraint(["flow_id", "tenant_id"], ["flows.id", "flows.tenant_id"]),
)

telegram_link_codes = Table(
    "telegram_link_codes",
    metadata,
    Column("digest", LargeBinary, primary_key=True),
    Column("tenant_id", Uuid, ForeignKey("tenants.id"), nullable=False),
    Column("issued_at", DateTime(timezone=True), nullable=False),
    Column("used_at", DateTime(timezone=True)),
)

telegram_chats = Table(
    "telegram_chats",
    metadata,
    Column("tenant_id", Uuid, ForeignKey("tenants.id"), primary_key=True),
    Column("chat_id", BigInteger, nullable=False),
    Column("linked_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

# One row per planned instant of a flow: taking the row is what keeps a planned cycle unique (ADR 0041, ADR 0046).
cycles = Table(
    "cycles",
    metadata,
    Column("flow_id", Uuid, primary_key=True),
    Column("planned_at", DateTime(timezone=True), primary_key=True),
    Column("tenant_id", Uuid, nullable=False),
    # Empty while the cycle is in progress: the row is taken before the cycle runs.
    Column("outcome", Text),
    Column("started_at", DateTime(timezone=True)),
    Column("delay_seconds", Integer),
    Column("steps", JSON),
    Column("absent_sources", JSON),
    Column("failure", JSON),
    Column("documents", JSON),
    Column("input_tokens", Integer),
    Column("output_tokens", Integer),
    Column("cost_usd", Numeric),
    ForeignKeyConstraint(["flow_id", "tenant_id"], ["flows.id", "flows.tenant_id"]),
)

closed_positions = Table(
    "closed_positions",
    metadata,
    Column("id", Uuid, primary_key=True, server_default=text("gen_random_uuid()")),
    Column("tenant_id", Uuid, nullable=False),
    Column("flow_id", Uuid, nullable=False),
    Column("asset", Text, nullable=False),
    Column("side", Text, nullable=False),
    Column("leverage", Integer, nullable=False),
    Column("margin", Numeric, nullable=False),
    Column("open_price", Numeric, nullable=False),
    Column("opened_at", DateTime(timezone=True), nullable=False),
    Column("opening_cycle", DateTime(timezone=True)),
    Column("close_price", Numeric, nullable=False),
    Column("closed_at", DateTime(timezone=True), nullable=False),
    Column("closing_cycle", DateTime(timezone=True)),
    Column("fees", Numeric, nullable=False),
    Column("reason", Text, nullable=False),
    ForeignKeyConstraint(["flow_id", "tenant_id"], ["flows.id", "flows.tenant_id"]),
)

# A collected value is a fact of a past cycle: it is only ever added (R1.3.8).
source_samples = Table(
    "source_samples",
    metadata,
    Column("id", BigInteger, Identity(), primary_key=True),
    Column("tenant_id", Uuid, nullable=False),
    Column("flow_id", Uuid, nullable=False),
    Column("cycle_planned_at", DateTime(timezone=True), nullable=False),
    Column("source", Text, nullable=False),
    Column("asset", Text),
    Column("reference_at", DateTime(timezone=True), nullable=False),
    Column("collected_at", DateTime(timezone=True), nullable=False),
    Column("sample_values", JSON, nullable=False),
    ForeignKeyConstraint(["flow_id", "tenant_id"], ["flows.id", "flows.tenant_id"]),
    Index("source_samples_of_cycle", "flow_id", "cycle_planned_at"),
)

# The last reading of each account, replaced at every reconciliation (R1.6.2, ADR 0045).
account_readings = Table(
    "account_readings",
    metadata,
    Column("account_id", Uuid, primary_key=True),
    Column("tenant_id", Uuid, ForeignKey("tenants.id"), nullable=False),
    Column("read_at", DateTime(timezone=True), nullable=False),
    Column("open_assets", JSON, nullable=False),
)

# Recorded once while the case lasts: unique among the cases not resolved (R1.6.2, ADR 0045).
unattributable_items = Table(
    "unattributable_items",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("tenant_id", Uuid, ForeignKey("tenants.id"), nullable=False),
    Column("account_id", Uuid, nullable=False),
    Column("kind", Text, nullable=False),
    Column("reference", Text, nullable=False),
    Column("asset", Text),
    Column("amount", Numeric, nullable=False),
    Column("detected_at", DateTime(timezone=True), nullable=False),
    Column("resolved_at", DateTime(timezone=True)),
    Index(
        "unattributable_items_open_case_unique",
        "tenant_id",
        "account_id",
        "kind",
        "reference",
        unique=True,
        postgresql_where=text("resolved_at IS NULL"),
    ),
)
