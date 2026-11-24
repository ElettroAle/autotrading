from sqlalchemy import (
    ARRAY,
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    Date,
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
    # The day the credentials stop working and who gave it, both empty while unknown (R6.2.2).
    Column("expires_on", Date),
    Column("expiry_source", Text),
    CheckConstraint("expiry_source IN ('read', 'entered')", name="accounts_expiry_source_known"),
    CheckConstraint("(expires_on IS NULL) = (expiry_source IS NULL)", name="accounts_expiry_complete"),
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
    # The day the key stops working and who gave it, both empty while unknown (R6.2.2).
    Column("expires_on", Date),
    Column("expiry_source", Text),
    CheckConstraint("expiry_source IN ('read', 'entered')", name="provider_keys_expiry_source_known"),
    CheckConstraint("(expires_on IS NULL) = (expiry_source IS NULL)", name="provider_keys_expiry_complete"),
)

# The credentials a tenant gave an adapter of a source: the public values in clear, the secret ones sealed, the expiry
# the user gave and the instant the provider refused them (R4.1.2, R6.2.2).
source_credentials = Table(
    "source_credentials",
    metadata,
    Column("tenant_id", Uuid, ForeignKey("tenants.id"), primary_key=True),
    Column("adapter", Text, primary_key=True),
    Column("public_values", JSON, nullable=False),
    Column("key_version", Integer, nullable=False),
    Column("ciphertext", LargeBinary, nullable=False),
    Column("expires_on", Date),
    Column("expiry_source", Text),
    Column("rejected_at", DateTime(timezone=True)),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint("expiry_source IN ('read', 'entered')", name="source_credentials_expiry_source_known"),
    CheckConstraint("(expires_on IS NULL) = (expiry_source IS NULL)", name="source_credentials_expiry_complete"),
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

# At most one address per tenant for its notifications by email, valid at once without a verification (R3.5.2).
notification_emails = Table(
    "notification_emails",
    metadata,
    Column("tenant_id", Uuid, ForeignKey("tenants.id"), primary_key=True),
    Column("address", Text, nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

# The mail server the emails of a tenant leave from, one per tenant, with its password sealed for the worker (ADR
# server-di-posta-per-tenant).
notification_mail_servers = Table(
    "notification_mail_servers",
    metadata,
    Column("tenant_id", Uuid, ForeignKey("tenants.id"), primary_key=True),
    Column("host", Text, nullable=False),
    Column("port", Integer, nullable=False),
    Column("security", Text, nullable=False),
    Column("username", Text, nullable=False),
    Column("sender", Text, nullable=False),
    Column("sealed_password", LargeBinary, nullable=False),
    Column("key_version", Integer, nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

# The channels the tenant chose for a type of event, for all its flows, empty for none; an event without a row goes to
# its default channels (R3.5.3, ADR canali-delle-notifiche-come-insieme).
notification_channels = Table(
    "notification_channels",
    metadata,
    Column("tenant_id", Uuid, ForeignKey("tenants.id"), primary_key=True),
    Column("event", Text, primary_key=True),
    Column("channels", ARRAY(Text), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

# The channels of a flow other than the general ones, for a type of event of the flow (R3.5.3).
notification_channel_exceptions = Table(
    "notification_channel_exceptions",
    metadata,
    Column("tenant_id", Uuid, primary_key=True),
    Column("flow_id", Uuid, primary_key=True),
    Column("event", Text, primary_key=True),
    Column("channels", ARRAY(Text), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    ForeignKeyConstraint(
        ["flow_id", "tenant_id"], ["flows.id", "flows.tenant_id"], name="notification_channel_exceptions_flow"
    ),
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
    # The cycle called the model, even when the call failed before its usage was known (R1.4.6).
    Column("model_called", Boolean, nullable=False, server_default=text("false")),
    # How many calls the decision of the agent tried; empty when it never asked, or before the attempts were kept
    # (R1.4.9).
    Column("model_attempts", Integer),
    # What started the cycle: its schedule or the user (R6.5.2); a row taken before the cycle runs is planned.
    Column("trigger", Text, nullable=False, server_default="scheduled"),
    # Every attempt of a step that failed; empty in the cycles recorded before the attempts were kept (ADR
    # errori-temporanei-ritentati-in-ogni-passo-del-ciclo).
    Column("failed_attempts", JSON),
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
    # The adapter of the source that read the value (R4.1.1); the migration gave the values collected before theirs.
    Column("adapter", Text, nullable=False),
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

# The deposits, withdrawals and transfers of every account, read with the executions from the same cursor (ADR
# movimenti-del-conto-nel-registro-con-cursore).
account_movements = Table(
    "account_movements",
    metadata,
    Column("id", BigInteger, Identity(), primary_key=True),
    Column("tenant_id", Uuid, ForeignKey("tenants.id"), nullable=False),
    Column("account_id", Uuid, nullable=False),
    Column("movement_id", Text, nullable=False),
    Column("amount", Numeric, nullable=False),
    Column("moved_at", DateTime(timezone=True), nullable=False),
    Column("recorded_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint("tenant_id", "account_id", "movement_id", "moved_at", name="account_movements_once"),
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


# The alerts of every tenant: one open per cause, forgotten 90 days after they resolve (R6.2.3, ADR
# avvisi-nel-contesto-delle-notifiche).
alerts = Table(
    "alerts",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("tenant_id", Uuid, ForeignKey("tenants.id"), nullable=False),
    Column("kind", Text, nullable=False),
    Column("resource_kind", Text, nullable=False),
    Column("resource_id", Uuid, nullable=False),
    Column("resource_name", Text, nullable=False),
    Column("detail", Text, nullable=False),
    Column("cause_key", Text, nullable=False),
    Column("readings", JSON, nullable=False),
    Column("opened_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("resolved_at", DateTime(timezone=True)),
    Index(
        "alerts_open_cause_unique", "tenant_id", "cause_key", unique=True, postgresql_where=text("resolved_at IS NULL")
    ),
    Index("alerts_newest", "tenant_id", text("opened_at DESC"), text("id DESC")),
)

# The thresholds told for each expiry of a key, once each: a new date of the key is told again (R6.2.2).
key_expiry_notices = Table(
    "key_expiry_notices",
    metadata,
    Column("tenant_id", Uuid, ForeignKey("tenants.id"), primary_key=True),
    Column("key_kind", Text, primary_key=True),
    Column("key_id", Uuid, primary_key=True),
    Column("expires_on", Date, primary_key=True),
    Column("threshold", Integer, primary_key=True),
    Column("notified_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint("key_kind IN ('account', 'provider', 'source')", name="key_expiry_notices_kind_known"),
)

inbox_notifications = Table(
    "inbox_notifications",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("tenant_id", Uuid, ForeignKey("tenants.id"), nullable=False),
    Column("notified_at", DateTime(timezone=True), nullable=False),
    Column("icon", Text, nullable=False),
    Column("title", Text, nullable=False),
    Column("text", Text, nullable=False),
    Column("targets", JSON, nullable=False),
    Column("read_at", DateTime(timezone=True)),
    Index("inbox_notifications_newest", "tenant_id", text("notified_at DESC"), text("id DESC")),
)

# The accounts of the simulated exchange: the virtual balance, the leverage set on each asset, the open positions, the
# protections and the history of the executions and movements, each of one tenant (R6.3.2, ADR
# exchange-simulato-con-porte-di-lettura-e-scrittura).
simulated_accounts = Table(
    "simulated_accounts",
    metadata,
    Column("account_id", Uuid, primary_key=True),
    Column("tenant_id", Uuid, ForeignKey("tenants.id"), nullable=False),
    Column("balance", Numeric, nullable=False),
    Column("leverages", JSON, nullable=False),
)

simulated_positions = Table(
    "simulated_positions",
    metadata,
    Column("account_id", Uuid, ForeignKey("simulated_accounts.account_id"), primary_key=True),
    Column("coin", Text, primary_key=True),
    Column("tenant_id", Uuid, ForeignKey("tenants.id"), nullable=False),
    Column("direction", Text, nullable=False),
    Column("size", Numeric, nullable=False),
    Column("leverage", Integer, nullable=False),
    Column("entry_price", Numeric, nullable=False),
    Column("margin", Numeric, nullable=False),
    Column("maintenance_rate", Numeric, nullable=False),
    Column("mark_price", Numeric),
)

simulated_protections = Table(
    "simulated_protections",
    metadata,
    Column("order_id", Text, primary_key=True),
    Column("tenant_id", Uuid, ForeignKey("tenants.id"), nullable=False),
    Column("account_id", Uuid, ForeignKey("simulated_accounts.account_id"), nullable=False),
    Column("coin", Text, nullable=False),
    Column("kind", Text, nullable=False),
    Column("closing_direction", Text, nullable=False),
    Column("trigger_price", Numeric, nullable=False),
    Column("client_order_id", Uuid, nullable=False, unique=True),
    Column("placed_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    # Set once the protection stops waiting: executed, cancelled, or gone with its position.
    Column("closed_at", DateTime(timezone=True)),
)

simulated_fills = Table(
    "simulated_fills",
    metadata,
    Column("id", BigInteger, Identity(), primary_key=True),
    Column("tenant_id", Uuid, ForeignKey("tenants.id"), nullable=False),
    Column("account_id", Uuid, ForeignKey("simulated_accounts.account_id"), nullable=False),
    Column("exchange_order_id", Text, nullable=False),
    Column("client_order_id", Uuid),
    Column("coin", Text, nullable=False),
    Column("is_buy", Boolean, nullable=False),
    Column("size", Numeric, nullable=False),
    Column("price", Numeric, nullable=False),
    Column("fee", Numeric, nullable=False),
    Column("realized_pnl", Numeric, nullable=False),
    Column("start_position", Numeric, nullable=False),
    Column("liquidation", Boolean, nullable=False),
    Column("executed_at", DateTime(timezone=True), nullable=False),
    Index("simulated_fills_of_account", "tenant_id", "account_id", "executed_at"),
)

simulated_movements = Table(
    "simulated_movements",
    metadata,
    Column("id", BigInteger, Identity(), primary_key=True),
    Column("tenant_id", Uuid, ForeignKey("tenants.id"), nullable=False),
    Column("account_id", Uuid, ForeignKey("simulated_accounts.account_id"), nullable=False),
    Column("amount", Numeric, nullable=False),
    Column("moved_at", DateTime(timezone=True), nullable=False),
)
