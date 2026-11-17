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
    # The fields the exchange declares public, in clear; empty for an account registered before they were kept
    # (Bug 401, ADR campi-pubblici-del-conto-conservati-in-chiaro).
    Column("exchange_account_public_fields", JSON),
    # Empty once the account is removed: the row stays for its history, the credentials do not (ADR 0025).
    Column("credentials_key_version", Integer),
    Column("credentials_ciphertext", LargeBinary),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("removed_at", DateTime(timezone=True)),
    # In percent of the expected balance, 1 unless the user sets another (R3.3.1).
    Column("deviation_threshold", Numeric, nullable=False, server_default=text("1")),
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
# Only a draft, or a draft archived, has no account (ADR 0124).
flows = Table(
    "flows",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("tenant_id", Uuid, ForeignKey("tenants.id"), nullable=False),
    Column("account_id", Uuid),
    Column("name", Text, nullable=False),
    Column("status", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    # Stamped by the database on every change into "active": the first cycle falls there (R1.2.1, ADR 0042).
    Column("cycle_anchor", DateTime(timezone=True)),
    Column("first_started_at", DateTime(timezone=True)),
    Column("pause_reason", Text),
    # The openings suspended for maximum loss, with the threshold passed, and their last resume (R3.2.2).
    Column("openings_suspension_reason", Text),
    Column("openings_suspended_at", DateTime(timezone=True)),
    Column("openings_resumed_at", DateTime(timezone=True)),
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

flow_capital_changes = Table(
    "flow_capital_changes",
    metadata,
    Column("id", BigInteger, Identity(), primary_key=True),
    Column("flow_id", Uuid, nullable=False),
    Column("tenant_id", Uuid, nullable=False),
    Column("changed_at", DateTime(timezone=True), nullable=False),
    Column("previous_capital", Numeric, nullable=False),
    Column("new_capital", Numeric, nullable=False),
    Column("user_id", Text, nullable=False),
    Column("version", Integer, nullable=False),
    Column("reason", Text, nullable=False),
    Column("amount", Numeric, nullable=False),
    Column("value_before", Numeric),
    Column("cashed_profit", Numeric, nullable=False),
    ForeignKeyConstraint(["flow_id", "tenant_id"], ["flows.id", "flows.tenant_id"]),
    ForeignKeyConstraint(["flow_id", "version"], ["flow_versions.flow_id", "flow_versions.version"]),
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

# The decisions of the agent in a cycle, one row by asset in the order it gave them (ADR
# decisioni-del-ciclo-registrate-per-asset).
cycle_decisions = Table(
    "cycle_decisions",
    metadata,
    Column("flow_id", Uuid, primary_key=True),
    Column("planned_at", DateTime(timezone=True), primary_key=True),
    Column("position", Integer, primary_key=True),
    Column("tenant_id", Uuid, nullable=False),
    Column("asset", Text, nullable=False),
    Column("action", Text, nullable=False),
    Column("direction", Text),
    Column("confidence", Integer),
    Column("reasoning", Text, nullable=False),
    ForeignKeyConstraint(["flow_id", "planned_at"], ["cycles.flow_id", "cycles.planned_at"]),
)

# The equity of every cycle that read the state of its flow, partitioned by month like a time series (ADR 0120).
equity_snapshots = Table(
    "equity_snapshots",
    metadata,
    Column("flow_id", Uuid, primary_key=True),
    Column("planned_at", DateTime(timezone=True), primary_key=True),
    Column("tenant_id", Uuid, nullable=False),
    Column("equity", Numeric, nullable=False),
    Column("allocated_capital", Numeric, nullable=False),
    Column("realized_pnl", Numeric, nullable=False),
    Column("unrealized_pnl", Numeric, nullable=False),
    Column("fees", Numeric, nullable=False),
    Column("funding", Numeric, nullable=False),
    Column("cashed_profit", Numeric, nullable=False),
    ForeignKeyConstraint(["flow_id", "tenant_id"], ["flows.id", "flows.tenant_id"]),
    postgresql_partition_by="RANGE (planned_at)",
)

forecasts = Table(
    "forecasts",
    metadata,
    Column("flow_id", Uuid, primary_key=True),
    Column("asset", Text, primary_key=True),
    Column("horizon_minutes", Integer, primary_key=True),
    Column("made_at", DateTime(timezone=True), primary_key=True),
    Column("tenant_id", Uuid, nullable=False),
    Column("last_price", Numeric, nullable=False),
    Column("predicted_price", Numeric, nullable=False),
    Column("history_days", Integer, nullable=False),
    Column("shortened", Boolean, nullable=False),
    Column("actual_price", Numeric),
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
    # The PnL the exchange reported for the closing, when it reported one (ADR 0070).
    Column("realized_pnl", Numeric),
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
    # The balance the next comparison starts from, and the comparison of this reading (R3.3.1): empty for a reading
    # saved before the balances were compared, and the comparison for the first reading of an account.
    Column("reference_balance", Numeric),
    Column("expected_balance", Numeric),
    Column("read_balance", Numeric),
)

# At most one alarm open per account, also with two cycles of the account together (R3.3.1).
reconciliation_alarms = Table(
    "reconciliation_alarms",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("tenant_id", Uuid, ForeignKey("tenants.id"), nullable=False),
    Column("account_id", Uuid, nullable=False),
    Column("expected_balance", Numeric, nullable=False),
    Column("read_balance", Numeric, nullable=False),
    Column("deviation_percent", Numeric, nullable=False),
    Column("opened_at", DateTime(timezone=True), nullable=False),
    Column("confirmed_at", DateTime(timezone=True)),
    Index(
        "reconciliation_alarms_open_unique",
        "tenant_id",
        "account_id",
        unique=True,
        postgresql_where=text("confirmed_at IS NULL"),
    ),
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

# The ledger of the executions of every account: written once, never changed (ADR 0063).
account_fills = Table(
    "account_fills",
    metadata,
    Column("id", BigInteger, Identity(), primary_key=True),
    Column("tenant_id", Uuid, ForeignKey("tenants.id"), nullable=False),
    Column("account_id", Uuid, nullable=False),
    Column("fill_id", Text, nullable=False),
    Column("exchange_order_id", Text, nullable=False),
    Column("flow_id", Uuid),
    Column("order_id", Uuid),
    Column("kind", Text, nullable=False),
    Column("platform_order", Boolean, nullable=False),
    Column("asset", Text, nullable=False),
    Column("size", Numeric, nullable=False),
    Column("price", Numeric, nullable=False),
    Column("fee", Numeric, nullable=False),
    Column("realized_pnl", Numeric, nullable=False),
    Column("start_position", Numeric, nullable=False),
    Column("liquidation", Boolean, nullable=False),
    Column("executed_at", DateTime(timezone=True), nullable=False),
    Column("recorded_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint("tenant_id", "account_id", "fill_id", "exchange_order_id", name="account_fills_once"),
)

account_funding = Table(
    "account_funding",
    metadata,
    Column("id", BigInteger, Identity(), primary_key=True),
    Column("tenant_id", Uuid, ForeignKey("tenants.id"), nullable=False),
    Column("account_id", Uuid, nullable=False),
    Column("flow_id", Uuid),
    Column("asset", Text, nullable=False),
    Column("amount", Numeric, nullable=False),
    Column("paid_at", DateTime(timezone=True), nullable=False),
    Column("recorded_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint("tenant_id", "account_id", "asset", "paid_at", name="account_funding_once"),
)

# Where the next reading of the executions of each account starts (ADR 0063).
account_fill_cursors = Table(
    "account_fill_cursors",
    metadata,
    Column("account_id", Uuid, primary_key=True),
    Column("tenant_id", Uuid, ForeignKey("tenants.id"), nullable=False),
    Column("last_executed_at", DateTime(timezone=True), nullable=False),
)

# The running totals the cycle reads instead of the ledger, changed only with a new row of the ledger (ADR 0063).
flow_totals = Table(
    "flow_totals",
    metadata,
    Column("flow_id", Uuid, primary_key=True),
    Column("tenant_id", Uuid, ForeignKey("tenants.id"), nullable=False),
    Column("realized_pnl", Numeric, nullable=False),
    Column("fees", Numeric, nullable=False),
    Column("funding", Numeric, nullable=False),
)

flow_position_totals = Table(
    "flow_position_totals",
    metadata,
    Column("flow_id", Uuid, primary_key=True),
    Column("asset", Text, primary_key=True),
    Column("tenant_id", Uuid, ForeignKey("tenants.id"), nullable=False),
    Column("size", Numeric, nullable=False),
)

# The messages to external systems until they are delivered: the queue of the outbox carries only their identity (ADR
# outbox-delle-integrazioni-esterne-con-procrastinate).
outbox_messages = Table(
    "outbox_messages",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("tenant_id", Uuid, ForeignKey("tenants.id"), nullable=False),
    Column("integration", Text, nullable=False),
    Column("payload", JSON, nullable=False),
    Column("status", Text, nullable=False, server_default="pending"),
    Column("attempts", Integer, nullable=False, server_default="0"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("last_error", Text),
)

# The exit plan in force of each open position of a flow, replaced at every opening and removed at the closing (R3.1.1).
flow_exit_plans = Table(
    "flow_exit_plans",
    metadata,
    Column("flow_id", Uuid, primary_key=True),
    Column("asset", Text, primary_key=True),
    Column("tenant_id", Uuid, nullable=False),
    Column("target_price", Numeric),
    Column("stop_price", Numeric),
    Column("invalidation", Text),
    ForeignKeyConstraint(["flow_id", "tenant_id"], ["flows.id", "flows.tenant_id"]),
)


# The protections the platform placed for the positions of the flows; a removed one stays, so that its execution read
# later still belongs to its flow (R3.1.2).
flow_protections = Table(
    "flow_protections",
    metadata,
    Column("client_order_id", Uuid, primary_key=True),
    Column("tenant_id", Uuid, nullable=False),
    Column("account_id", Uuid, nullable=False),
    Column("flow_id", Uuid, nullable=False),
    Column("asset", Text, nullable=False),
    Column("kind", Text, nullable=False),
    Column("trigger_price", Numeric, nullable=False),
    Column("exchange_order_id", Text, nullable=False),
    Column("placed_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("removed_at", DateTime(timezone=True)),
    ForeignKeyConstraint(["account_id", "tenant_id"], ["accounts.id", "accounts.tenant_id"]),
    ForeignKeyConstraint(["flow_id", "tenant_id"], ["flows.id", "flows.tenant_id"]),
)


# Every emergency closing a tenant launched: when, on which scope, and the outcome of each flow (R3.2.3).
emergency_closings = Table(
    "emergency_closings",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("tenant_id", Uuid, ForeignKey("tenants.id"), nullable=False),
    Column("closed_at", DateTime(timezone=True), nullable=False),
    Column("scope_kind", Text, nullable=False),
    Column("scope_id", Uuid),
    Column("outcome", JSON, nullable=False),
)
